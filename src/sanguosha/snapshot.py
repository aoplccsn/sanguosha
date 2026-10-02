"""Versioned, data-only authoritative GameSession snapshots.

The handler registry is reconstructed from the ruleset. Only mutable game data is
stored; decoding accepts dataclasses and enums from this package, never imports
arbitrary modules named by persisted data.
"""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from enum import Enum
from importlib import import_module
import json
from types import MappingProxyType
from typing import Any

from sanguosha.decisions.ai import AIDecisionProvider
from sanguosha.engine.resolution import ResolutionStack
from sanguosha.engine.rng import PythonRandomSource
from sanguosha.model.enums import Identity
from sanguosha.model.ids import CharacterId, PlayerId
from sanguosha.pregame import Pregame, SetupStage
from sanguosha.session import GameSession


SNAPSHOT_SCHEMA_VERSION = 1


def _type_name(value: Any) -> str:
    kind = type(value)
    if not kind.__module__.startswith("sanguosha."):
        raise TypeError(f"unsupported snapshot type: {kind!r}")
    return f"{kind.__module__}:{kind.__qualname__}"


def _encode(value: Any) -> Any:
    if isinstance(value, Enum):
        return {"$enum": _type_name(value), "value": value.value}
    if value is None or type(value) in (bool, int, float, str):
        return value
    if is_dataclass(value) and not isinstance(value, type):
        return {"$dataclass": _type_name(value), "fields": {
            item.name: _encode(getattr(value, item.name)) for item in fields(value)
        }}
    if isinstance(value, tuple):
        return {"$tuple": [_encode(item) for item in value]}
    if isinstance(value, (set, frozenset)):
        return {"$set": [_encode(item) for item in sorted(value, key=repr)]}
    if isinstance(value, (dict, MappingProxyType)):
        return {"$dict": [[_encode(key), _encode(item)] for key, item in value.items()]}
    if isinstance(value, list):
        return [_encode(item) for item in value]
    raise TypeError(f"unsupported snapshot value: {type(value)!r}")


def _resolve(name: str) -> type:
    module_name, separator, class_name = name.partition(":")
    if not separator or not module_name.startswith("sanguosha.") or not class_name.isidentifier():
        raise ValueError(f"invalid snapshot class: {name!r}")
    kind = getattr(import_module(module_name), class_name)
    if not isinstance(kind, type):
        raise ValueError(f"invalid snapshot class: {name!r}")
    return kind


def _decode(value: Any) -> Any:
    if isinstance(value, list):
        return [_decode(item) for item in value]
    if not isinstance(value, dict):
        return value
    if "$enum" in value:
        kind = _resolve(value["$enum"])
        if not issubclass(kind, Enum):
            raise ValueError("snapshot enum type is invalid")
        return kind(value["value"])
    if "$dataclass" in value:
        kind = _resolve(value["$dataclass"])
        if not is_dataclass(kind):
            raise ValueError("snapshot dataclass type is invalid")
        return kind(**{name: _decode(item) for name, item in value["fields"].items()})
    if "$tuple" in value:
        return tuple(_decode(item) for item in value["$tuple"])
    if "$set" in value:
        return set(_decode(item) for item in value["$set"])
    if "$dict" in value:
        return {_decode(key): _decode(item) for key, item in value["$dict"]}
    raise ValueError("unrecognized snapshot value")


def snapshot_session(session: GameSession) -> bytes:
    """Capture every mutable engine continuation and RNG state."""
    engine = session.engine
    if session.rng is None:
        raise ValueError("session has no restorable random source")
    data = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "state": _encode(engine.state),
        "stack": _encode(engine.stack.snapshot()),
        "pending_request": _encode(engine.pending_request),
        "status": _encode(engine.status),
        "last_result": _encode(engine.last_result),
        "next_frame": engine._next_frame,
        "seen_action_ids": _encode(engine._seen_action_ids),
        "seen_request_ids": _encode(engine._seen_request_ids),
        "max_steps": engine.max_steps,
        "events": _encode(session.events.events),
        "rng_state": _encode(session.rng._random.getstate()),
        "human_id": str(session.human_id),
        "character_names": _encode(session.character_names),
        "declined_nullification_windows": _encode(session.declined_nullification_windows),
        "move_reactions": _encode(
            session.engine.reaction_provider.__self__.reactions
            if session.engine.reaction_provider is not None else []),
    }
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def restore_session(blob: bytes) -> GameSession:
    """Restore a complete rules engine; reject incompatible schema versions."""
    data = json.loads(blob)
    version = data.get("schema_version")
    if version != SNAPSHOT_SCHEMA_VERSION:
        raise ValueError(f"incompatible GameSnapshot schema: {version!r}")
    state = _decode(data["state"])
    military = state.ruleset_id == "classic-military"
    generals = {pid: CharacterId(player.character_id) for pid, player in state.players.items()}
    with_generals = military and all(not str(general).startswith("blank-") for general in generals.values())
    setup = None
    if with_generals:
        identities = {pid: Identity(player.identity) for pid, player in state.players.items()}
        setup = Pregame(PythonRandomSource(0), identities, (), SetupStage.COMPLETE, generals)
    session = GameSession.new_game(seed=0, military=military, setup=setup)
    engine = session.engine
    engine.state = state
    engine.stack = ResolutionStack()
    for frame in _decode(data["stack"]):
        engine.stack.push(frame)
    engine.pending_request = _decode(data["pending_request"])
    engine.status = _decode(data["status"])
    engine.last_result = _decode(data["last_result"])
    engine._next_frame = data["next_frame"]
    engine._seen_action_ids = _decode(data["seen_action_ids"])
    engine._seen_request_ids = _decode(data["seen_request_ids"])
    engine.max_steps = data["max_steps"]
    session.events.events = _decode(data["events"])
    session.rng._random.setstate(_decode(data["rng_state"]))
    session.human_id = PlayerId(data["human_id"])
    session.ai = AIDecisionProvider(session.human_id)
    session.character_names = _decode(data["character_names"])
    session.declined_nullification_windows = _decode(data["declined_nullification_windows"])
    if engine.reaction_provider is not None:
        engine.reaction_provider.__self__.reactions = _decode(data.get("move_reactions", []))
    return session
