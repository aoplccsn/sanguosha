"""Desktop shell connecting human clicks to the shared Decision API."""
import os

from PySide6.QtCore import QTimer, Qt, QAbstractAnimation, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget,
)

from sanguosha.engine.phases import END_PLAY_PHASE
from sanguosha.engine.card_effects import SlashEffectAction
from sanguosha.engine.card_use import UseCardAction
from sanguosha.engine.events import CardUsedEvent, CardMovedEvent
from sanguosha.engine.requests import PASS_RESPONSE, Decision, RequestType
from sanguosha.model.ids import CardInstanceId, PlayerId
from sanguosha.model.zones import ZoneType
from sanguosha.model.state import GameStatus
from sanguosha.projection import project_for_human
from sanguosha.session import GameSession
from sanguosha.pregame import Pregame, SetupStage

from .decision_controller import DecisionController
from .game_table import GameTable
from .hand_view import HandView
from .interaction import InteractionState, UiMode
from .log_panel import LogPanel
from .theme import QSS
from .resources import RESOURCES
from .general_detail import GeneralDetailPanel, SkillBar
from .pregame_dialog import PregameDialog
from .timing import HUMAN_DECISION_TIMEOUT_MS, DECISION_TIMER_TICK_MS

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
        self._skill_mode: str | None = None
        self._detail_dialog = None
        self._pregame_dialog = None
        self.interaction = InteractionState()
        self._tick_scheduled = False
        self._closed = False
        self._tick_timer = QTimer(self)
        self._tick_timer.setSingleShot(True)
        self._tick_timer.timeout.connect(self._tick)
        self._decision_timer = QTimer(self)
        self._decision_timer.timeout.connect(self._decision_countdown)
        self._decision_request_id = None
        self._decision_remaining_ms = HUMAN_DECISION_TIMEOUT_MS
        self._decision_timer.setInterval(DECISION_TIMER_TICK_MS)
        root = QWidget()
        root.setObjectName("root")
        self.setStyleSheet(QSS)
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(6, 5, 6, 5)
        layout.setSpacing(3)
        header = QHBoxLayout()
        self.standard_game_button = QPushButton('标准开局预览 · 随机身份与十选一')
        self.standard_game_button.setObjectName('standard-new-game')
        self.standard_game_button.clicked.connect(lambda checked=False: self.start_standard_game())
        if military:
            header.addWidget(self.standard_game_button)
        self.new_game_button = QPushButton("五将练习")
        self.new_game_button.setObjectName("new-game")
        self.new_game_button.clicked.connect(self.start_new_game)
        header.addWidget(self.new_game_button)
        self.status_label = QLabel("五人身份局 · 军争 160 张" if military else "五人身份局 · 普通杀 / 闪 / 桃")
        self.status_label.setObjectName("status")
        header.addWidget(self.status_label)
        self.result_new_game = QPushButton('再来一局')
        self.result_new_game.clicked.connect(lambda checked=False: self.start_standard_game() if self.military else self.start_new_game())
        self.result_new_game.hide()
        header.addWidget(self.result_new_game)
        self.result_exit = QPushButton('退出')
        self.result_exit.clicked.connect(self.close)
        self.result_exit.hide()
        header.addWidget(self.result_exit)
        header.addStretch()
        layout.addLayout(header)
        self.table = GameTable()
        self.table.setMinimumHeight(400)
        self.table.player_selected.connect(self._player_clicked)
        self.table.detail_requested.connect(self._show_general_detail)
        self.table.shared_card_selected.connect(self._shared_card_clicked)
        layout.addWidget(self.table, stretch=1)
        self.skill_bar = SkillBar()
        self.skill_bar.selected.connect(self._skill_clicked)
        layout.addWidget(self.skill_bar, alignment=Qt.AlignHCenter)
        self.hand = HandView()
        self.hand.card_selected.connect(self._card_clicked)
        self.decision = DecisionController()
        self.decision.value_selected.connect(self._submit_value)
        layout.addWidget(self.decision)
        layout.addWidget(self.hand)
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
        """Keep the five-general practice match for the existing T7-A tests."""
        self._install_session(GameSession.new_game(military=self.military, five_generals=self.military))

    def start_standard_game(self, seed: int | None = None) -> None:
        if not self.military:
            return
        if self._pregame_dialog is not None:
            self._pregame_dialog.close()
        self._tick_timer.stop()
        self._decision_timer.stop()
        setup = Pregame.create(seed)
        dialog = PregameDialog(setup, self)
        self._pregame_dialog = dialog
        def finished(result):
            if result == QDialog.DialogCode.Accepted and setup.stage is SetupStage.COMPLETE and not self._closed:
                self._install_session(GameSession.new_game(military=True, setup=setup))
            if self._pregame_dialog is dialog:
                self._pregame_dialog = None
        dialog.finished.connect(finished)
        dialog.show()

    def _install_session(self, session: GameSession) -> None:
        self._tick_timer.stop()
        self._decision_timer.stop()
        self._decision_request_id = None
        self._tick_scheduled = False
        self.session = session
        self._seen_events = 0
        self._selected_cards.clear()
        self._selected_players.clear()
        self._selected_shared_card = None
        self._skill_mode = None
        self.interaction.reset()
        self.log.clear()
        self.table.vfx.reset()
        self.result_new_game.hide()
        self.result_exit.hide()
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
        self._decision_timer.stop()
        self._tick_scheduled = False
        if self._pregame_dialog is not None:
            self._pregame_dialog.close()
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
        if value == "ui.decline_nullification" and self.session is not None:
            self.session.decline_nullification_window()
            value = PASS_RESPONSE
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
                card_id = self.interaction.card_id
                request = self.session.engine.pending_request if self.session else None
                if request and CardInstanceId(card_id) in request.eligible_card_ids:
                    value = CardInstanceId(card_id)
                elif request and f'virtual:qingguo:{card_id}' in request.eligible_card_ids:
                    value = f'virtual:qingguo:{card_id}'
                else:
                    value = f'virtual:wusheng:{card_id}'
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
            self._decision_timer.stop()
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

    def _decision_countdown(self) -> None:
        if self._closed or self.session is None:
            self._decision_timer.stop()
            return
        request = self.session.engine.pending_request
        if request is None or request.request_id != self._decision_request_id or request.player_id != self.session.human_id:
            self._decision_timer.stop()
            return
        self._decision_remaining_ms = max(0, self._decision_remaining_ms - DECISION_TIMER_TICK_MS)
        self.table.panels[str(self.session.human_id)].set_decision_progress(
            self._decision_remaining_ms / HUMAN_DECISION_TIMEOUT_MS)
        if self._decision_remaining_ms == 0:
            self._decision_timer.stop()
            self._submit_value(request.timeout_value())

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
            virtual = f'virtual:{self._skill_mode}:{card_id}' if self._skill_mode else None
            if virtual and virtual in request.choices:
                self._skill_mode = None
                self._submit_value(virtual)
                return
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
            if (CardInstanceId(card_id) in request.eligible_card_ids or
                    f'virtual:wusheng:{card_id}' in request.eligible_card_ids or
                    f'virtual:qingguo:{card_id}' in request.eligible_card_ids):
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

    def _show_general_detail(self, player_id: str) -> None:
        if self.session is None or self.session.skills is None:
            return
        pid = PlayerId(player_id)
        character = self.session.skills.characters.get(self.session.state.players[pid].character_id)
        if character is None:
            return
        view = project_for_human(self.session.state, self.session.definitions,
                                 self.session.human_id, self.session.character_names)
        player_view = next(p for p in view.players if p.player_id == pid)
        request = self.session.engine.pending_request
        choices = (request.choices + tuple(map(str, request.eligible_card_ids))
                   if request is not None and request.player_id == pid else ())
        self._detail_dialog = GeneralDetailPanel(player_view, character, self.session.skills.skills,
                                                 self.session.state.players[pid], self.session.state,
                                                 choices, self)
        self._detail_dialog.show()

    def _skill_clicked(self, skill_id: str) -> None:
        if self.session is None:
            return
        request = self.session.engine.pending_request
        if request is None or request.player_id != self.session.human_id:
            return
        direct = f'skill:{skill_id}'
        virtual = f'virtual:{skill_id}'
        if direct in request.choices:
            self._submit_value(direct)
        elif virtual in request.eligible_card_ids:
            self._submit_value(virtual)
        elif any(str(choice).startswith(virtual + ':') for choice in (*request.choices, *request.eligible_card_ids)):
            self._skill_mode = skill_id
            self.decision.prompt_label.setText(f'【{self.session.skills.skills[skill_id].name}】请选择材料牌')

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
        session.clear_finished_nullification_windows()
        skipped = False
        while session.pass_unavailable_nullification():
            skipped = True
        if skipped:
            self._schedule_tick()
        view = project_for_human(session.state, session.definitions, session.human_id, session.character_names)
        request = session.engine.pending_request
        human_request = request if request is not None and request.player_id == session.human_id else None
        if human_request is not None and human_request.request_id != self._decision_request_id:
            self._decision_request_id = human_request.request_id
            self._decision_remaining_ms = HUMAN_DECISION_TIMEOUT_MS
            self._decision_timer.start()
        elif human_request is None:
            self._decision_timer.stop()
            self._decision_request_id = None
        request_id = human_request.request_id if human_request else None
        if request_id != self.interaction.request_id:
            self._selected_shared_card = None
            self._skill_mode = None
            mode = (UiMode.RESPONDING_WITH_CARD if human_request and human_request.request_type is RequestType.RESPOND_WITH_CARD
                    else UiMode.MULTI_CARD_DISCARDING if human_request and human_request.request_type is RequestType.CHOOSE_CARDS
                    else UiMode.IDLE)
            self.interaction.reset(request_id, mode)
        targets = set(self.interaction.legal_targets)
        if human_request and human_request.request_type in (RequestType.CHOOSE_PLAYER, RequestType.CHOOSE_PLAYERS):
            targets = set(map(str, human_request.allowed_player_ids))
        attack = self._attack_context() if human_request and human_request.request_type is RequestType.RESPOND_WITH_CARD else None
        selected_targets=set(self._selected_players) or ({self.interaction.target_id} if self.interaction.target_id else set())
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
        elif self.interaction.card_id and targets:
            card = next((c for c in view.hand if str(c.card_id) == self.interaction.card_id), None)
            if card:
                selected_names = [p.name for p in view.players if str(p.player_id) in selected_targets]
                notice = f"【{card.name}】· " + ("目标：" + "、".join(selected_names) if selected_names else "请选择金框目标")
                art = card.definition_id
        self.table.render(view, targets, selected_targets,
                          attack[0] if attack else None, attack[1] if attack else None,
                          self._attack_definition() if attack else None, self._selected_shared_card,
                          notice, art)
        preview_kind = ('protect' if art in ('basic.peach', 'basic.dodge') else
                        'control' if art and art.startswith('trick.') else 'attack')
        self.table.vfx.set_preview(str(session.human_id) if self.interaction.card_id else None,
                                   selected_targets, preview_kind)
        for pid, panel in self.table.panels.items():
            panel.set_pending_responder(bool(request and str(request.player_id) == pid and
                                             not next((p.active for p in view.players if str(p.player_id) == pid), False)))
            panel.set_decision_progress(
                self._decision_remaining_ms / HUMAN_DECISION_TIMEOUT_MS
                if human_request and pid == str(session.human_id) else
                1.0 if request and str(request.player_id) == pid else None)
        if session.skills is not None:
            actor = session.state.players[session.human_id]
            character = session.skills.characters.get(actor.character_id)
            choices = (human_request.choices + tuple(map(str, human_request.eligible_card_ids))
                       if human_request is not None else ())
            self.skill_bar.render(character, session.skills.skills, actor, session.state, choices)
            self.skill_bar.setVisible(character is not None)
        else:
            self.skill_bar.hide()
        selectable: set[str] = set()
        if human_request is not None:
            if human_request.request_type is RequestType.CHOOSE_OPTION:
                selectable = {choice[4:] for choice in human_request.choices if choice.startswith("use:")}
                selectable.update(choice.split(':', 2)[2] for choice in human_request.choices
                                  if choice.startswith('virtual:wusheng:'))
            elif human_request.request_type in (RequestType.RESPOND_WITH_CARD, RequestType.CHOOSE_CARD, RequestType.CHOOSE_CARDS):
                selectable = set(map(str, human_request.eligible_card_ids))
                selectable.update(choice.split(':',2)[2] for choice in human_request.eligible_card_ids
                                  if isinstance(choice,str) and choice.startswith(('virtual:wusheng:', 'virtual:qingguo:')))
        selected_cards = set(self._selected_cards)
        if self.interaction.card_id:
            selected_cards.add(self.interaction.card_id)
        self.hand.render(view.hand, selectable, selected_cards,
                         bool(human_request and human_request.request_type is RequestType.RESPOND_WITH_CARD))
        if view.result is not None:
            self.status_label.setText(f"游戏结束 · {view.result}")
            self.decision.render(view.result, [])
            self.result_new_game.show()
            self.result_exit.show()
        else:
            self.result_new_game.hide()
            self.result_exit.hide()
            active = next((player.name for player in view.players if player.active), "等待开局")
            phase = {"preparation": "准备", "judgment": "判定", "draw": "摸牌", "play": "出牌", "discard": "弃牌", "finish": "结束"}.get(view.current_phase, view.current_phase)
            self.status_label.setText(f"第 {view.turn_number} 回合 · {active} · {phase}阶段")
            self._render_request(human_request, view, attack)
        for event in session.events.events[self._seen_events:]:
            self.log.add_event(event, session.state, session.definitions)
            card_id = getattr(event, 'card_id', None)
            definition_id = (getattr(event, 'response_definition_id', '') or
                             (str(session.state.cards[card_id].definition_id) if card_id in session.state.cards else ''))
            names = {str(player.player_id): player.name for player in view.players}
            self.table.vfx.consume(event, definition_id=definition_id,
                                   human_id=str(session.human_id), names=names)
            if isinstance(event, CardUsedEvent):
                definition_id = session.state.cards[event.card_id].definition_id
                card_name = session.definitions.get(definition_id).name
                source = next((p.name for p in view.players if p.player_id == event.player_id), "玩家")
                self.table.play_public_event(f"{source} 使用【{card_name}】", str(definition_id))
            elif (isinstance(event, CardMovedEvent) and
                  event.from_zone.zone_type is ZoneType.JUDGMENT and
                  event.to_zone.zone_type is ZoneType.JUDGMENT and event.card_ids):
                cid = event.card_ids[0]
                definition_id = session.state.cards[cid].definition_id
                source = next((p.name for p in view.players if p.player_id == event.from_zone.player_id), "玩家")
                target = next((p.name for p in view.players if p.player_id == event.to_zone.player_id), "玩家")
                self.table.play_public_event(f"判定牌转移 · {source} → {target}", str(definition_id))
            elif isinstance(event, CardMovedEvent) and event.reason == "discard":
                self.table.play_public_event(f"弃置 {len(event.card_ids)} 张牌", "card_back")
            if getattr(event, "event_type", None) == "judgment_result":
                card_id = event.metadata.get("card_id")
                if card_id in session.state.cards:
                    definition_id = session.state.cards[card_id].definition_id
                    self.table.play_judgment(
                        session.definitions.get(definition_id).name,
                        str(definition_id), bool(event.metadata.get("matched")))
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
                labels = {'virtual:spear':'丈八蛇矛', 'skill:rende':'仁德',
                          'skill:zhiheng':'制衡', 'skill:jijiang':'激将',
                          'skill:kurou':'苦肉', 'skill:qingnang':'青囊'}
                labels['skill:jieyin'] = '结姻'
                def option_label(choice):
                    if choice.startswith('virtual:wusheng:'):
                        material = choice.split(':',2)[2]
                        card = next((card for card in view.hand if str(card.card_id) == material), None)
                        return f'武圣 · {card.name} {card.suit}{card.rank}' if card else '武圣 · 红牌'
                    return labels.get(choice,choice)
                actions.extend((option_label(choice),choice,True)
                               for choice in request.choices
                               if not choice.startswith('use:') and choice != END_PLAY_PHASE)
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
            elif request.required_definition_id == 'trick.nullification':
                trick = next((getattr(frame.action,'definition_id') for frame in
                              reversed(self.session.engine.stack.snapshot())
                              if getattr(frame.action,'definition_id','').startswith(('trick.','delayed.'))), None)
                card_name = self.session.definitions.get(trick).name if trick else '锦囊'
                target = next((p.name for p in view.players if p.player_id == request.subject_player_id), '目标')
                prompt = f'【{card_name}】正在对{target}结算 · 你可以使用【无懈可击】'
            else:
                prompt = request.prompt + " · 请选择响应牌"
            if request.allow_pass:
                actions.append(("不出", PASS_RESPONSE, True))
            if self.session.nullification_window_id(request) is not None:
                actions.append(("本次均不响应", "ui.decline_nullification", True))
            actions.append(("确认响应", "ui.confirm_response", self.interaction.card_id is not None))
            if 'virtual:spear' in request.eligible_card_ids:
                actions.append(('丈八蛇矛（两张手牌）','virtual:spear',True))
            if 'virtual:hujia' in request.eligible_card_ids:
                actions.append(('护驾 · 请魏角色出闪','virtual:hujia',True))
            if 'virtual:jijiang' in request.eligible_card_ids:
                actions.append(('激将 · 请蜀角色出杀','virtual:jijiang',True))
            if self.interaction.card_id:
                actions.append(("取消", "ui.cancel", True))
        elif kind is RequestType.CHOOSE_CARDS:
            count = len(self._selected_cards)
            prompt = request.prompt + f"：已选 {count}/{request.min_count} 张。"
            ordered = tuple(card_id for card_id in request.eligible_card_ids if str(card_id) in self._selected_cards)
            verb = '确认选择' if '仁德' in request.prompt or '制衡' in request.prompt else '确认弃置'
            actions.append((f"{verb} {count}/{request.min_count}", ordered,
                            request.min_count <= count <= request.max_count))
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
