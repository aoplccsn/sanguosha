"""Desktop shell connecting human clicks to the shared Decision API."""
import os

from PySide6.QtCore import QTimer, Qt, QAbstractAnimation, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget,
)

from sanguosha.engine.phases import END_PLAY_PHASE
from sanguosha.engine.card_effects import SlashEffectAction
from sanguosha.engine.card_use import UseCardAction
from sanguosha.engine.requests import PASS_RESPONSE, Decision, RequestType
from sanguosha.model.ids import CardInstanceId, PlayerId
from sanguosha.model.state import GameStatus
from sanguosha.projection import project_for_human
from sanguosha.session import GameSession

from .decision_controller import DecisionController
from .game_table import GameTable
from .hand_view import HandView
from .interaction import InteractionState, UiMode
from .log_panel import LogPanel
from .theme import QSS
from .resources import RESOURCES

NORMAL_AI_DELAY_MS = 500


class MainWindow(QMainWindow):
    def __init__(self, *, military=True) -> None:
        super().__init__()
        self.military = military
        self.setWindowTitle("三国杀 · 五人身份局")
        self.resize(1440, 900)
        self.setMinimumSize(1280, 720)
        self.session: GameSession | None = None
        self._seen_events = 0
        self._selected_cards: set[str] = set()
        self._selected_players: set[str] = set()
        self._selected_shared_card: str | None = None
        self.interaction = InteractionState()
        self._tick_scheduled = False
        self._closed = False
        self._tick_timer = QTimer(self)
        self._tick_timer.setSingleShot(True)
        self._tick_timer.timeout.connect(self._tick)
        root = QWidget()
        root.setObjectName("root")
        self.setStyleSheet(QSS)
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(6, 5, 6, 5)
        layout.setSpacing(3)
        header = QHBoxLayout()
        self.new_game_button = QPushButton("开始游戏")
        self.new_game_button.setObjectName("new-game")
        self.new_game_button.clicked.connect(self.start_new_game)
        header.addWidget(self.new_game_button)
        self.status_label = QLabel("五人身份局 · 军争 160 张" if military else "五人身份局 · 普通杀 / 闪 / 桃")
        self.status_label.setObjectName("status")
        header.addWidget(self.status_label)
        header.addStretch()
        layout.addLayout(header)
        self.table = GameTable()
        self.table.setMinimumHeight(400)
        self.table.player_selected.connect(self._player_clicked)
        self.table.shared_card_selected.connect(self._shared_card_clicked)
        layout.addWidget(self.table, stretch=1)
        self.hand = HandView()
        self.hand.card_selected.connect(self._card_clicked)
        layout.addWidget(self.hand)
        self.decision = DecisionController()
        self.decision.value_selected.connect(self._submit_value)
        layout.addWidget(self.decision)
        self.log = LogPanel()
        self.log_toggle = QPushButton("战报  ▾")
        self.log_toggle.setProperty("action", True)
        self.log_toggle.setCheckable(True)
        self.log_toggle.setChecked(False)
        self.log_toggle.toggled.connect(self.log.setVisible)
        header.addWidget(self.log_toggle)
        layout.addWidget(self.log, alignment=Qt.AlignRight)
        self.log.setVisible(False)

    def start_new_game(self) -> None:
        self._tick_timer.stop()
        self._tick_scheduled = False
        self.session = GameSession.new_game(military=self.military)
        self._seen_events = 0
        self._selected_cards.clear()
        self._selected_players.clear()
        self._selected_shared_card = None
        self.interaction.reset()
        self.log.clear()
        self._render()
        self._schedule_tick()

    def _schedule_tick(self) -> None:
        if not self._closed and not self._tick_scheduled:
            self._tick_scheduled = True
            delay = 0 if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("SANGUOSHA_FAST_AI") else NORMAL_AI_DELAY_MS
            self._tick_timer.start(delay)

    def closeEvent(self, event) -> None:
        self._closed = True
        self._tick_timer.stop()
        self._tick_scheduled = False
        for animation in self.findChildren(QAbstractAnimation):
            animation.stop()
        super().closeEvent(event)

    def _tick(self) -> None:
        self._tick_scheduled = False
        if self._closed or self.session is None:
            return
        try:
            progressed = self.session.step_auto()
        except Exception as exc:
            self.decision.render(f"游戏错误：{exc}", [])
            return
        self._render()
        if progressed:
            self._schedule_tick()

    def _submit_value(self, value: object) -> None:
        if isinstance(value, tuple) and len(value) == 2 and value[0] == 'ui.toggle_card':
            self._card_clicked(value[1])
            return
        if value == "ui.cancel":
            self._selected_players.clear()
            self._selected_cards.clear()
            request = self.session.engine.pending_request if self.session else None
            mode = UiMode.RESPONDING_WITH_CARD if request and request.request_type is RequestType.RESPOND_WITH_CARD else UiMode.IDLE
            self.interaction.reset(request.request_id if request else None, mode)
            self._render()
            return
        if value == "ui.confirm_play":
            self._confirm_play()
            return
        if value == "ui.confirm_response":
            if self.interaction.card_id:
                value = CardInstanceId(self.interaction.card_id)
            else:
                return
        if value == "ui.confirm_target":
            if self.interaction.target_id:
                value = PlayerId(self.interaction.target_id)
            else:
                return
        if value == "ui.confirm_shared":
            if self._selected_shared_card is None:
                return
            value = CardInstanceId(self._selected_shared_card)
        if self.session is None or self.session.engine.pending_request is None:
            return
        request = self.session.engine.pending_request
        try:
            self.session.submit_human(Decision(request.request_id, request.player_id, value))
        except Exception as exc:
            self.decision.render(f"选择无效：{exc}", [])
            self._render()
            return
        self._selected_cards.clear()
        self._selected_players.clear()
        self._selected_shared_card = None
        self.interaction.reset()
        self._render()
        self._schedule_tick()

    def _preview_targets(self, card_id: str) -> set[str]:
        """Read the registered rule; previewing does not mutate engine state."""
        assert self.session is not None
        action = UseCardAction("ui-preview", self.session.human_id, CardInstanceId(card_id))
        handler = self.session.engine.registry.handler_for(action)
        rule = handler.validator.validate_card(self.session.state, self.session.human_id, CardInstanceId(card_id))
        return set(map(str, rule.target_candidates(self.session.state, self.session.human_id))) if rule.requires_target_selection else set()

    def _confirm_play(self) -> None:
        if self.session is None or self.interaction.card_id is None:
            return
        request = self.session.engine.pending_request
        if request is None or request.request_type is not RequestType.CHOOSE_OPTION:
            return
        card_id = self.interaction.card_id
        target_id = self.interaction.target_id
        rule=self.session.engine.registry.handler_for(UseCardAction('ui-confirm',self.session.human_id,card_id)).validator.rule_for(self.session.state,card_id)
        low,high=rule.target_bounds(self.session.state,self.session.human_id,card_id) if hasattr(rule,'target_bounds') else (1,1)
        if self.interaction.legal_targets:
            if high>1:
                if not low<=len(self._selected_players)<=high:
                    return
            elif target_id not in self.interaction.legal_targets:
                return
        try:
            self.session.submit_human(Decision(request.request_id, request.player_id, f"use:{card_id}"))
            target_request = self.session.engine.pending_request
            if target_request and target_request.request_type is RequestType.CHOOSE_PLAYER:
                if target_id is None or PlayerId(target_id) not in target_request.allowed_player_ids:
                    raise ValueError("目标已不再合法")
                self.session.submit_human(Decision(target_request.request_id, target_request.player_id, PlayerId(target_id)))
            elif target_request and target_request.request_type is RequestType.CHOOSE_PLAYERS:
                self.session.submit_human(Decision(target_request.request_id,target_request.player_id,
                    tuple(pid for pid in target_request.allowed_player_ids if str(pid) in self._selected_players)))
        except Exception as exc:
            self.interaction.reset()
            self._render()
            self.decision.prompt_label.setText(f"出牌未完成：{exc}")
            return
        self.interaction.reset()
        self._selected_cards.clear()
        self._selected_players.clear()
        self._render()
        self._schedule_tick()

    def _card_clicked(self, card_id: str) -> None:
        if self.session is None or self.session.engine.pending_request is None:
            return
        request = self.session.engine.pending_request
        if request.player_id != self.session.human_id:
            return
        if request.request_type is RequestType.CHOOSE_OPTION:
            option = f"use:{card_id}"
            if option in request.choices:
                if self.interaction.card_id == card_id:
                    self.interaction.reset(request.request_id)
                else:
                    targets = self._preview_targets(card_id)
                    if not self.military and not targets:
                        self._submit_value(option)
                        return
                    self.interaction.select_card(card_id, targets)
                    self._selected_players.clear()
                self._render()
        elif request.request_type in (RequestType.RESPOND_WITH_CARD, RequestType.CHOOSE_CARD):
            if CardInstanceId(card_id) in request.eligible_card_ids:
                if request.request_type is RequestType.RESPOND_WITH_CARD:
                    self.interaction.select_response(card_id)
                    self._render()
                else:
                    self._submit_value(CardInstanceId(card_id))
        elif request.request_type is RequestType.CHOOSE_CARDS:
            if CardInstanceId(card_id) in request.eligible_card_ids:
                if card_id in self._selected_cards:
                    self._selected_cards.remove(card_id)
                elif len(self._selected_cards) < request.max_count:
                    self._selected_cards.add(card_id)
                self._render()

    def _player_clicked(self, player_id: str) -> None:
        if self.session is None or self.session.engine.pending_request is None:
            return
        request = self.session.engine.pending_request
        if request.player_id != self.session.human_id:
            return
        if request.request_type is RequestType.CHOOSE_OPTION and player_id in self.interaction.legal_targets:
            card_id=self.interaction.card_id
            rule=self.session.engine.registry.handler_for(UseCardAction('ui-bounds',self.session.human_id,card_id)).validator.rule_for(self.session.state,card_id)
            low,high=rule.target_bounds(self.session.state,self.session.human_id,card_id) if hasattr(rule,'target_bounds') else (1,1)
            if high>1:
                if player_id in self._selected_players:
                    self._selected_players.remove(player_id)
                elif len(self._selected_players)<high:
                    self._selected_players.add(player_id)
            self.interaction.select_target(player_id)
            self._render()
        elif request.request_type is RequestType.CHOOSE_PLAYER and PlayerId(player_id) in request.allowed_player_ids:
            self.interaction.legal_targets = set(map(str, request.allowed_player_ids))
            self.interaction.select_target(player_id)
            self._render()
        elif request.request_type is RequestType.CHOOSE_PLAYERS and PlayerId(player_id) in request.allowed_player_ids:
            if player_id in self._selected_players:
                self._selected_players.remove(player_id)
            elif len(self._selected_players) < request.max_count:
                self._selected_players.add(player_id)
            self._render()

    def _shared_card_clicked(self, card_id: str) -> None:
        if self.session is None:
            return
        request = self.session.engine.pending_request
        if (request is None or request.player_id != self.session.human_id or
                request.request_type is not RequestType.CHOOSE_CARD or
                CardInstanceId(card_id) not in request.eligible_card_ids):
            return
        self._selected_shared_card = card_id
        self._render()

    def _render(self) -> None:
        if self.session is None:
            return
        session = self.session
        view = project_for_human(session.state, session.definitions, session.human_id, session.character_names)
        request = session.engine.pending_request
        human_request = request if request is not None and request.player_id == session.human_id else None
        request_id = human_request.request_id if human_request else None
        if request_id != self.interaction.request_id:
            self._selected_shared_card = None
            mode = (UiMode.RESPONDING_WITH_CARD if human_request and human_request.request_type is RequestType.RESPOND_WITH_CARD
                    else UiMode.MULTI_CARD_DISCARDING if human_request and human_request.request_type is RequestType.CHOOSE_CARDS
                    else UiMode.IDLE)
            self.interaction.reset(request_id, mode)
        targets = set(self.interaction.legal_targets)
        if human_request and human_request.request_type in (RequestType.CHOOSE_PLAYER, RequestType.CHOOSE_PLAYERS):
            targets = set(map(str, human_request.allowed_player_ids))
        attack = self._attack_context() if human_request and human_request.request_type is RequestType.RESPOND_WITH_CARD else None
        notice = art = None
        if human_request and human_request.required_definition_id == "trick.nullification":
            target = next((p.name for p in view.players if p.player_id == human_request.subject_player_id), "目标")
            frames = session.engine.stack.snapshot()
            trick = next((getattr(f.action, "definition_id") for f in reversed(frames)
                          if getattr(f.action, "definition_id", "").startswith("trick.")), None)
            trick_name = session.definitions.get(trick).name if trick else "锦囊"
            layer = next((int(f.local.get("round", 0)) for f in reversed(frames)
                          if type(f.action).__name__ == "NullificationWindow"), 0)
            notice = f"当前锦囊：【{trick_name}】\n作用目标：{target} · 无懈层数：{layer}"
            art = trick or "trick.nullification"
        elif view.current_phase == "judgment":
            notice, art = "判定中 · 等待判定牌", "delayed.lightning"
        selected_targets=set(self._selected_players) or ({self.interaction.target_id} if self.interaction.target_id else set())
        self.table.render(view, targets, selected_targets,
                          attack[0] if attack else None, attack[1] if attack else None,
                          self._attack_definition() if attack else None, self._selected_shared_card,
                          notice, art)
        selectable: set[str] = set()
        if human_request is not None:
            if human_request.request_type is RequestType.CHOOSE_OPTION:
                selectable = {choice[4:] for choice in human_request.choices if choice.startswith("use:")}
            elif human_request.request_type in (RequestType.RESPOND_WITH_CARD, RequestType.CHOOSE_CARD, RequestType.CHOOSE_CARDS):
                selectable = set(map(str, human_request.eligible_card_ids))
        selected_cards = set(self._selected_cards)
        if self.interaction.card_id:
            selected_cards.add(self.interaction.card_id)
        self.hand.render(view.hand, selectable, selected_cards,
                         bool(human_request and human_request.request_type is RequestType.RESPOND_WITH_CARD))
        if view.result is not None:
            self.status_label.setText(f"游戏结束 · {view.result}")
            self.decision.render(view.result, [])
        else:
            active = next((player.name for player in view.players if player.active), "等待开局")
            phase = {"preparation": "准备", "judgment": "判定", "draw": "摸牌", "play": "出牌", "discard": "弃牌", "finish": "结束"}.get(view.current_phase, view.current_phase)
            self.status_label.setText(f"第 {view.turn_number} 回合 · {active} · {phase}阶段")
            self._render_request(human_request, view, attack)
        for event in session.events.events[self._seen_events:]:
            self.log.add_event(event, session.state, session.definitions)
        self._seen_events = len(session.events.events)

    def _attack_context(self) -> tuple[str, str] | None:
        if self.session is None:
            return None
        for frame in reversed(self.session.engine.stack.snapshot()):
            if isinstance(frame.action, SlashEffectAction):
                return str(frame.action.source_id), str(frame.action.target_id)
        return None

    def _attack_definition(self):
        for frame in reversed(self.session.engine.stack.snapshot()):
            if isinstance(frame.action, SlashEffectAction):
                virtual=getattr(frame.action,'virtual_card',None)
                return virtual.definition_id if virtual else self.session.state.cards[frame.action.card_id].definition_id
        return 'basic.slash'

    def _render_request(self, request, view, attack=None) -> None:
        if request is None:
            self.decision.render("AI 行动中…", [])
            return
        kind = request.request_type
        actions: list[tuple[str, object, bool]] = []
        if kind is RequestType.CHOOSE_OPTION:
            if self.interaction.card_id:
                card = next((c for c in view.hand if str(c.card_id) == self.interaction.card_id), None)
                card_name = card.name if card else "卡牌"
                if self.interaction.legal_targets:
                    chosen = next((p.name for p in view.players if str(p.player_id) == self.interaction.target_id), None)
                    prompt = f"已选【{card_name}】 · 目标：{chosen or '请选择金框目标'}"
                    ready = self.interaction.target_id is not None
                    rule=self.session.engine.registry.handler_for(UseCardAction('ui-prompt',self.session.human_id,self.interaction.card_id)).validator.rule_for(self.session.state,self.interaction.card_id)
                    low,high=rule.target_bounds(self.session.state,self.session.human_id,self.interaction.card_id) if hasattr(rule,'target_bounds') else (1,1)
                    if high>1:
                        ready=low<=len(self._selected_players)<=high
                        prompt=f'已选【{card_name}】 · 已选 {len(self._selected_players)} 名目标 · 确定或重铸'
                else:
                    prompt, ready = f"已选【{card_name}】 · 请确认使用", True
                actions = [("确定", "ui.confirm_play", ready), ("取消", "ui.cancel", True)]
            else:
                if END_PLAY_PHASE in request.choices:
                    actions.append(("结束出牌阶段", END_PLAY_PHASE, True))
                actions.extend(('丈八蛇矛' if choice=='virtual:spear' else choice,choice,True)
                               for choice in request.choices if not choice.startswith('use:') and choice!=END_PLAY_PHASE)
                prompt = "出牌阶段 · 请选择可用手牌"
        elif kind is RequestType.CHOOSE_PLAYER:
            chosen = next((p.name for p in view.players if str(p.player_id) == self.interaction.target_id), None)
            prompt = f"选择目标 · {chosen or '点击金框玩家'}"
            actions = [("确定", "ui.confirm_target", chosen is not None)]
        elif kind is RequestType.RESPOND_WITH_CARD:
            if attack and request.required_definition_id=='basic.dodge':
                attacker = next((p.name for p in view.players if str(p.player_id) == attack[0]), attack[0])
                defender = next((p.name for p in view.players if str(p.player_id) == attack[1]), "你")
                prompt = f"{attacker} 对{defender}使用了【杀】 · 请选择【闪】响应"
            else:
                prompt = request.prompt + " · 请选择响应牌"
            if request.allow_pass:
                actions.append(("不出", PASS_RESPONSE, True))
            actions.append(("确认响应", "ui.confirm_response", self.interaction.card_id is not None))
            if 'virtual:spear' in request.eligible_card_ids:
                actions.append(('丈八蛇矛（两张手牌）','virtual:spear',True))
            if self.interaction.card_id:
                actions.append(("取消", "ui.cancel", True))
        elif kind is RequestType.CHOOSE_CARDS:
            count = len(self._selected_cards)
            prompt = request.prompt + f"：已选 {count}/{request.min_count} 张。"
            ordered = tuple(card_id for card_id in request.eligible_card_ids if str(card_id) in self._selected_cards)
            actions.append((f"确认弃置 {count}/{request.min_count}", ordered, count == request.min_count))
            owned_hand={str(c.card_id) for c in view.hand}
            for cid in request.eligible_card_ids:
                if str(cid) not in owned_hand:
                    actions.append((self._public_card_label(cid,view),('ui.toggle_card',str(cid)),True))
        elif kind is RequestType.CHOOSE_CARD:
            shared_ids = {str(card.card_id) for card in view.shared_cards}
            shared_request = bool(shared_ids.intersection(map(str, request.eligible_card_ids)))
            prompt = request.prompt + ("（在桌心选牌，再确认）" if shared_request else "（点击手牌）")
            owned_hand={str(c.card_id) for c in view.hand}
            actions.extend((self._public_card_label(cid,view),cid,True) for cid in request.eligible_card_ids if str(cid) not in owned_hand)
            if shared_request:
                actions.append(("确认选择", "ui.confirm_shared", self._selected_shared_card is not None))
        elif kind is RequestType.CHOOSE_PLAYERS:
            count = len(self._selected_players)
            prompt = f"请选择 {request.min_count} 名玩家：已选 {count} 名。"
            ordered = tuple(pid for pid in request.allowed_player_ids if str(pid) in self._selected_players)
            actions.append(("确认选择", ordered, request.min_count <= count <= request.max_count))
        elif kind is RequestType.YES_NO:
            prompt = request.prompt
            actions = [("是", True, True), ("否", False, True)]
        else:
            prompt = request.prompt
        self.decision.render(prompt, actions)
        public={str(card.card_id):card for card in (*view.shared_cards,
            *(card for player in view.players for card in (*player.equipment,*player.judgments)))}
        for button,(_,value,_) in zip(self.decision.buttons,actions):
            cid=value[1] if isinstance(value,tuple) and len(value)==2 and value[0]=='ui.toggle_card' else value
            card=public.get(cid) if isinstance(cid,str) else None
            if card:
                button.setIcon(QIcon(RESOURCES.card_art(card.definition_id)))
                button.setIconSize(QSize(35,46))
            if kind is RequestType.CHOOSE_CARD and isinstance(cid, str) and cid in {str(c.card_id) for c in view.shared_cards}:
                button.hide()

    def _public_card_label(self,cid,view):
        public=(*view.shared_cards,*(card for player in view.players for card in (*player.equipment,*player.judgments)))
        card=next((card for card in public if str(card.card_id)==str(cid)),None)
        return f'{card.name} {card.suit}{card.rank}' if card else '目标背面手牌'
