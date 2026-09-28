"""Public match log; hidden cards are shown only as counts."""

from PySide6.QtWidgets import QTextEdit

from sanguosha.engine.events import (
    CardMovedEvent, CardRespondedEvent, CardUsedEvent, DamageDealtEvent,
    DyingRequiredEvent, Event, GameEndedEvent, HpRecoveredEvent,
    KillRewardEvent, LordPenaltyEvent, PhaseStartedEvent, PlayerDiedEvent,
    TurnStartedEvent,
)
from sanguosha.model.zones import ZoneType
from sanguosha.engine.card_registry import CardDefinitionRegistry
from sanguosha.model.state import GameState


def describe_event(event: object, state: GameState, definitions: CardDefinitionRegistry) -> str | None:
    def name(player_id: object) -> str:
        if player_id not in state.players:
            return '系统'
        seat = state.players[player_id].seat
        return "你" if seat == 0 else f"玩家{seat + 1}"

    phases = {
        "preparation": "准备", "judgment": "判定", "draw": "摸牌",
        "play": "出牌", "discard": "弃牌", "finish": "结束",
    }
    if isinstance(event, Event) and event.event_type == "game-start":
        return "游戏开始。主公先行动。"
    if isinstance(event, TurnStartedEvent):
        return f"{name(event.player_id)} 的第 {event.turn_number} 回合开始。"
    if isinstance(event, PhaseStartedEvent):
        return f"{name(event.player_id)} 进入{phases.get(event.phase.value, event.phase.value)}阶段。"
    if isinstance(event, CardMovedEvent):
        if event.to_zone.zone_type is ZoneType.HAND and event.from_zone.zone_type is ZoneType.DRAW_PILE:
            return f"{name(event.to_zone.player_id)} 摸了 {len(event.card_ids)} 张牌。"
        if event.reason == "discard" or "cleanup" in event.event_id:
            return f"{name(event.actor_id)} 弃置了 {len(event.card_ids)} 张牌。"
    if isinstance(event, CardUsedEvent):
        card_name = definitions.get(event.virtual_definition_id or state.cards[event.card_id].definition_id).name
        return f"{name(event.player_id)} 使用【{card_name}】，目标：{', '.join(map(name, event.target_ids)) or '自己'}。"
    if isinstance(event, CardRespondedEvent):
        card_name = definitions.get(event.response_definition_id or state.cards[event.card_id].definition_id).name
        return f"{name(event.player_id)} 打出【{card_name}】。"
    if isinstance(event, DamageDealtEvent):
        return f"{name(event.target_id)} 受到 {event.amount} 点伤害，体力变为 {event.hp_after}。"
    if isinstance(event, HpRecoveredEvent):
        return f"{name(event.target_id)} 回复 {event.amount} 点体力。"
    if isinstance(event, DyingRequiredEvent):
        return f"{name(event.target_id)} 进入濒死。"
    if isinstance(event, PlayerDiedEvent):
        return f"{name(event.player_id)} 阵亡，身份：{event.identity.value}。"
    if isinstance(event, KillRewardEvent):
        return f"{name(event.killer_id)} 击杀反贼，奖励摸 {event.cards_drawn} 张牌。"
    if isinstance(event, LordPenaltyEvent):
        return f"主公误杀忠臣，弃置所有牌。"
    if isinstance(event, GameEndedEvent):
        return f"游戏结束：{event.label}。"
    return None


class LogPanel(QTextEdit):
    def __init__(self) -> None:
        super().__init__()
        self.setReadOnly(True)
        self.setObjectName("game-log")
        self.setFixedHeight(64)
        self.setMaximumWidth(520)
        self.document().setMaximumBlockCount(150)

    def add_event(self, event: object, state: GameState, definitions: CardDefinitionRegistry) -> None:
        line = describe_event(event, state, definitions)
        if line:
            self.append(line)
