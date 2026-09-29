"""Nested rule requests routed through real TCP clients, not engine-only calls."""

import asyncio
from dataclasses import replace

import pytest

from sanguosha.engine.card_use import UseCardAction
from sanguosha.engine.phases import PhaseAction
from sanguosha.engine.dying import DyingAction
from sanguosha.engine.events import CardRespondedEvent, VirtualResponseEvent
from sanguosha.engine.military_tricks import NullificationWindow
from sanguosha.engine.requests import Decision, PASS_RESPONSE
from sanguosha.engine.response import RespondWithCardAction
from sanguosha.engine.skills import JijiangUse
from sanguosha.model.enums import EquipmentSlot, Identity, Phase, Suit
from sanguosha.model.ids import PlayerId
from sanguosha.model.usage import PlayUsageState
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.multiplayer.protocol import decision_to_wire
from sanguosha.multiplayer.room import RoomPhase
from sanguosha.multiplayer.transport import GameClient, GameServer
from sanguosha.session import GameSession

from test_t6_military_basics import put


def configure(case, session):
    state = session.state
    state.current_player_id = "p1"
    state.current_phase = Phase.PLAY
    state.turn_number = 1
    state.play_usage = PlayUsageState("p1", 1)
    facts = {}
    if case in ("slash_dodge", "eight_trigrams", "wushuang", "iron_chain"):
        if case == "wushuang":
            state.players["p1"].character_id = "lvbu"
        if case == "iron_chain":
            state.players["p2"].chained = state.players["p3"].chained = True
        slash = put(session, "basic.fire_slash" if case == "iron_chain" else "basic.slash")
        if case == "slash_dodge":
            facts["dodge"] = put(session, "basic.dodge", "p2")
        if case == "wushuang":
            facts["dodges"] = [put(session, "basic.dodge", "p2") for _ in range(2)]
        if case == "eight_trigrams":
            put(session, "equipment.armor.eight_trigrams", "p2", ZoneType.EQUIPMENT, EquipmentSlot.ARMOR)
            top = state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
            state.cards[top] = replace(state.cards[top], suit=Suit.HEART)
        return UseCardAction(f"network-{case}", "p1", slash, ("p2",)), facts
    if case == "nullification_chain":
        facts["counters"] = [put(session, "trick.nullification", pid) for pid in ("p1", "p2")]
        return NullificationWindow("network-nullification_chain", "p4"), facts
    if case == "duel":
        duel = put(session, "trick.duel")
        facts["slashes"] = [put(session, "basic.fire_slash", "p2"), put(session, "basic.thunder_slash", "p1")]
        return UseCardAction("network-duel", "p1", duel, ("p2",)), facts
    if case == "amazing_grace":
        return UseCardAction("network-amazing_grace", "p1", put(session, "trick.amazing_grace")), facts
    if case == "dying_peaches":
        state.players["p2"].hp = -1
        facts["peaches"] = [put(session, "basic.peach", pid) for pid in ("p3", "p4")]
        return DyingAction("network-dying_peaches", "p2", "p1"), facts
    if case == "hujia":
        state.players["p2"].character_id = "caocao"
        facts["dodge"] = put(session, "basic.dodge", "p2")
        return RespondWithCardAction("network-hujia", "p1", "basic.dodge", "attack"), facts
    if case == "jijiang":
        state.players["p2"].identity = Identity.LORD
        state.players["p1"].identity = Identity.LOYALIST
        state.current_player_id = "p2"
        state.play_usage = PlayUsageState("p2", 1)
        facts["slash"] = put(session, "basic.slash", "p5")
        return JijiangUse("network-jijiang", "p2"), facts
    if case == "skill_trigger":
        state.players["p1"].character_id = "zhugeliang"
        return PhaseAction("network-skill_trigger", "p1", Phase.PREPARATION), facts
    raise AssertionError(case)


def decide(case, payload, facts):
    kind = payload["request_type"]
    pid = payload["player_id"]
    eligible = payload["eligible_card_ids"]
    if kind == "yes_no":
        return case in ("eight_trigrams", "skill_trigger")
    if kind == "respond_with_card":
        if case == "hujia" and pid == "p1" and "virtual:hujia" in eligible:
            return "virtual:hujia"
        wanted = {
            "slash_dodge": [facts.get("dodge")],
            "wushuang": facts.get("dodges", []),
            "nullification_chain": facts.get("counters", []),
            "duel": facts.get("slashes", []),
            "dying_peaches": facts.get("peaches", []),
            "hujia": [facts.get("dodge")],
            "jijiang": [facts.get("slash")],
        }.get(case, [])
        return next((cid for cid in wanted if cid in eligible), PASS_RESPONSE)
    if kind == "choose_player":
        return "p3" if case == "jijiang" else payload["allowed_player_ids"][0]
    if kind == "choose_card":
        return eligible[0]
    if kind == "choose_option":
        return payload["choices"][0]
    if kind in ("choose_cards", "choose_players"):
        options = eligible if kind == "choose_cards" else payload["allowed_player_ids"]
        return tuple(options[:payload["min_count"]])
    raise AssertionError((case, kind))


@pytest.mark.parametrize("case", [
    "slash_dodge", "eight_trigrams", "nullification_chain", "duel",
    "iron_chain", "amazing_grace", "dying_peaches", "wushuang",
    "hujia", "jijiang", "skill_trigger",
])
def test_nested_action_over_tcp(case):
    async def scenario():
        server = GameServer(host="127.0.0.1", port=0, timeout_seconds=30)
        await server.start()
        clients = [GameClient("127.0.0.1", server.port) for _ in range(5)]
        try:
            for index, client in enumerate(clients):
                await client.connect(f"human{index}")
            for client in clients:
                for _ in range(10):
                    message = await asyncio.wait_for(client.receive(), 3)
                    if message["type"] == "WELCOME" and message.get("seat_id"):
                        break
                else:
                    raise AssertionError("missing seat welcome")
            session = GameSession.new_game(seed=6, military=True, five_generals=True)
            server.room.session = session
            server.room.phase = RoomPhase.IN_GAME
            action, facts = configure(case, session)
            session.engine.start_action(action)
            server.room.pump()
            seen = []
            async def until(client, kind, request_id):
                for _ in range(200):
                    message = await asyncio.wait_for(client.receive(), 3)
                    matching_id = (message.get("request") or {}).get("request_id") if kind == "PENDING_REQUEST" else message.get("request_id")
                    if message["type"] == kind and matching_id == request_id:
                        return message
                    if message["type"] == "ERROR":
                        raise AssertionError(message["message"])
                raise AssertionError(f"missing {kind}: {request_id}")
            for _ in range(100):
                if not any(frame.action.action_id == action.action_id for frame in session.engine.stack.snapshot()):
                    break
                request = session.engine.pending_request
                assert request is not None, case
                client = clients[int(request.player_id[1:]) - 1]
                payload = (await until(client, "PENDING_REQUEST", request.request_id))["request"]
                assert payload["player_id"] == request.player_id
                seen.append((request.player_id, payload))
                await client.send("SUBMIT_DECISION", decision=decision_to_wire(
                    Decision(request.request_id, request.player_id, decide(case, payload, facts))))
                await until(client, "DECISION_RESULT", request.request_id)
            else:
                raise AssertionError("nested action did not complete")
            state = session.state
            state.__post_init__()
            assert not state.cards_in(ZoneRef(ZoneType.PROCESSING))
            if case in ("slash_dodge", "eight_trigrams", "wushuang"):
                assert state.players["p2"].hp == 4
            if case == "eight_trigrams":
                assert any(isinstance(e, VirtualResponseEvent) for e in session.events.events)
            if case == "nullification_chain":
                assert sum(isinstance(e, CardRespondedEvent) and e.card_id in facts["counters"] for e in session.events.events) == 2
            if case == "duel":
                assert state.players["p2"].hp == 3
            if case == "iron_chain":
                assert state.players["p2"].hp == state.players["p3"].hp == 3
            if case == "amazing_grace":
                assert sum(p["request_type"] == "choose_card" for _, p in seen) == 5
                assert not any(zone.card_ids for ref, zone in state.zones.items() if ref.zone_type is ZoneType.SPECIAL)
            if case == "dying_peaches":
                assert state.players["p2"].hp > 0
                assert {pid for pid, p in seen if p["required_definition_id"] == "basic.peach"} >= {"p3", "p4"}
            if case == "wushuang":
                assert sum(isinstance(e, CardRespondedEvent) and e.card_id in facts["dodges"] for e in session.events.events) == 2
            if case == "hujia":
                assert any(pid == "p2" for pid, _ in seen)
            if case == "jijiang":
                assert any(pid == "p5" and p["required_definition_id"] == "basic.slash" for pid, p in seen)
            if case == "skill_trigger":
                assert any(p["request_type"] == "yes_no" for _, p in seen)
        finally:
            for client in clients:
                await client.close()
            await server.close()
    asyncio.run(scenario())
