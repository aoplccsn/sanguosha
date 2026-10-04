"""Ink-style multiplayer lobby and projection-only game client."""

from __future__ import annotations

import asyncio
import socket

from PySide6.QtCore import QThread, QTimer, Signal, Qt
from PySide6.QtWidgets import (QDialog, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                               QApplication, QMessageBox, QPushButton, QScrollArea, QStackedWidget, QVBoxLayout, QWidget)

from sanguosha.content.characters.standard import ALL_GENERAL_POOL, ALL_SKILL_CATALOGUE
from sanguosha.engine.phases import END_PLAY_PHASE
from sanguosha.engine.events import (CardUsedEvent, TrickTargetsDeclaredEvent, CardRespondedEvent,
                                     VirtualResponseEvent, DamageDealtEvent, HpRecoveredEvent,
                                     PlayerDiedEvent, GameEndedEvent)
from sanguosha.model.enums import Identity
from sanguosha.projection import TableView
from sanguosha.multiplayer.protocol import (DEFAULT_GAME_PORT, deserialize_projection,
                                            decision_to_wire)
from sanguosha.engine.requests import Decision, PASS_RESPONSE

from .game_table import GameTable
from .hand_view import HandView
from .pregame_dialog import GeneralChoiceCard
from .theme import QSS
from sanguosha.multiplayer.transport import GameClient, GameServer
from sanguosha.relay.transport import HostRelayTransport, RelayGameClient
from sanguosha.session_store import clear_session, load_session, save_session
from sanguosha.settings import relay_url as default_relay_url

GUHUO_CARD_NAMES = {
    'basic.slash': '杀', 'basic.fire_slash': '火杀', 'basic.thunder_slash': '雷杀',
    'basic.dodge': '闪', 'basic.peach': '桃', 'basic.wine': '酒',
    'trick.nullification': '无懈可击', 'trick.ex_nihilo': '无中生有',
    'trick.dismantlement': '过河拆桥', 'trick.snatch': '顺手牵羊',
    'trick.duel': '决斗', 'trick.fire_attack': '火攻', 'trick.iron_chain': '铁索连环',
    'trick.savage_assault': '南蛮入侵', 'trick.archery_attack': '万箭齐发',
    'trick.god_salvation': '桃园结义', 'trick.amazing_grace': '五谷丰登',
    'trick.borrowed_sword': '借刀杀人',
}


class ServerThread(QThread):
    listening = Signal(int)
    failed = Signal(str)

    def __init__(self, port: int, parent=None):
        super().__init__(parent)
        self.port = port
        self.loop = None
        self.server = None

    def run(self):
        async def main():
            self.loop = asyncio.get_running_loop()
            self.server = GameServer(port=self.port)
            try:
                await self.server.start()
            except OSError as exc:
                self.failed.emit(str(exc))
                return
            self.listening.emit(self.server.port)
            try:
                await asyncio.Event().wait()
            finally:
                await self.server.close()
        try:
            asyncio.run(main())
        except asyncio.CancelledError:
            pass

    def stop(self):
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(lambda: [task.cancel() for task in asyncio.all_tasks(self.loop)])


class PublicHostThread(QThread):
    ready = Signal(int, str, str)
    failed = Signal(str)
    status = Signal(str)

    def __init__(self, relay_url: str, parent=None):
        super().__init__(parent)
        self.relay_url = relay_url
        self.loop = None
        self.game_server = None
        self.transport = None

    def run(self):
        async def main():
            self.loop = asyncio.get_running_loop()
            self.game_server = GameServer(host="127.0.0.1", port=0)
            try:
                await self.game_server.start()
                self.transport = HostRelayTransport(
                    self.relay_url, "127.0.0.1", self.game_server.port
                )
                code, token = await self.transport.start()
                self.ready.emit(self.game_server.port, code, token)
                self.status.emit("公网房间已建立")
                await asyncio.Event().wait()
            except Exception as exc:
                self.failed.emit(str(exc))
            finally:
                if self.transport:
                    await self.transport.close()
                if self.game_server:
                    await self.game_server.close()
        try:
            asyncio.run(main())
        except asyncio.CancelledError:
            pass

    def stop(self):
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(
                lambda: [task.cancel() for task in asyncio.all_tasks(self.loop)]
            )


class ClientThread(QThread):
    message = Signal(object)
    status = Signal(str)

    def __init__(self, host: str, port: int, name: str, parent=None):
        super().__init__(parent)
        self.host, self.port, self.name = host, port, name
        self.loop = None
        self.queue = None
        self.token = None
        self.stopping = False

    def send(self, kind: str, **fields):
        if self.loop and self.queue and not self.stopping:
            self.loop.call_soon_threadsafe(self.queue.put_nowait, (kind, fields))

    def run(self):
        async def main():
            self.loop = asyncio.get_running_loop()
            self.queue = asyncio.Queue()
            while not self.stopping:
                client = GameClient(self.host, self.port)
                try:
                    self.status.emit("重连中" if self.token else "连接中")
                    await client.connect(self.name, token=self.token)
                    self.status.emit("已连接")
                    async def receive():
                        while True:
                            msg = await client.receive()
                            if msg["type"] == "WELCOME" and msg.get("reconnect_token"):
                                self.token = msg["reconnect_token"]
                            self.message.emit(msg)
                    async def send():
                        while True:
                            kind, fields = await self.queue.get()
                            await client.send(kind, **fields)
                    tasks = [asyncio.create_task(receive()), asyncio.create_task(send())]
                    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                    for task in pending:
                        task.cancel()
                    for task in done:
                        task.result()
                except (OSError, ConnectionError, ValueError) as exc:
                    self.status.emit("已断线")
                    self.message.emit({"type": "ERROR", "message": str(exc)})
                finally:
                    await client.close()
                if not self.stopping:
                    await asyncio.sleep(1)
        try:
            asyncio.run(main())
        except asyncio.CancelledError:
            pass

    def stop(self):
        self.stopping = True
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(lambda: [task.cancel() for task in asyncio.all_tasks(self.loop)])


class RelayClientThread(ClientThread):
    def __init__(self, relay_url: str, room_code: str, name: str, token=None, parent=None):
        super().__init__("", 0, name, parent)
        self.relay_url = relay_url
        self.room_code = room_code.strip().upper()
        self.token = token

    def run(self):
        async def main():
            self.loop = asyncio.get_running_loop()
            self.queue = asyncio.Queue()
            while not self.stopping:
                client = RelayGameClient(self.relay_url, self.room_code)
                try:
                    self.status.emit("重连中" if self.token else "连接中")
                    await client.connect(self.name, token=self.token)
                    self.status.emit("已连接")

                    async def receive():
                        while True:
                            msg = await client.receive()
                            if msg["type"] == "WELCOME" and msg.get("reconnect_token"):
                                self.token = msg["reconnect_token"]
                                save_session(
                                    relay_url=self.relay_url,
                                    room_code=self.room_code,
                                    player_id=msg.get("seat_id", ""),
                                    reconnect_token=self.token,
                                )
                            if msg["type"] == "GAME_OVER":
                                clear_session()
                            self.message.emit(msg)

                    async def send():
                        while True:
                            kind, fields = await self.queue.get()
                            await client.send(kind, **fields)

                    tasks = [asyncio.create_task(receive()), asyncio.create_task(send())]
                    done, pending = await asyncio.wait(
                        tasks, return_when=asyncio.FIRST_COMPLETED
                    )
                    for task in pending:
                        task.cancel()
                    for task in done:
                        task.result()
                except (OSError, ConnectionError, ValueError) as exc:
                    self.status.emit("已断线")
                    self.message.emit({"type": "ERROR", "message": str(exc)})
                finally:
                    await client.close()
                if not self.stopping:
                    await asyncio.sleep(1)
        try:
            asyncio.run(main())
        except asyncio.CancelledError:
            pass


class MultiplayerWindow(QDialog):
    """Never receives GameState; host and guests use identical socket clients."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("三国杀 · 多人游戏")
        self.resize(1380, 860)
        self.setStyleSheet(QSS)
        self.server_thread = None
        self.public_host_thread = None
        self.client_thread = None
        self.room_code = None
        self.seat_id = None
        self.host_id = None
        self.room_phase = "OPEN"
        self.view: TableView | None = None
        self.request = None
        self.selected: set[str] = set()
        self.remaining_ms = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._countdown)
        self.timer.start(100)
        self.pages = QStackedWidget()
        layout = QVBoxLayout(self)
        layout.addWidget(self.pages)
        self._build_connect_page()
        self._build_lobby_page()
        self._build_game_page()
        QTimer.singleShot(0, self._offer_reconnect)

    def _build_connect_page(self):
        page = QWidget()
        box = QVBoxLayout(page)
        title = QLabel("五人身份局 · 多人游戏")
        title.setAlignment(Qt.AlignCenter)
        box.addWidget(title)
        self.name_edit = QLineEdit("玩家")
        self.name_edit.setPlaceholderText("玩家名称")
        self.room_code_edit = QLineEdit()
        self.room_code_edit.setMaxLength(8)
        self.room_code_edit.setPlaceholderText("房间码")
        self.relay_url_edit = QLineEdit(default_relay_url())
        for label, field in (("玩家名称", self.name_edit), ("房间码", self.room_code_edit)):
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            row.addWidget(field)
            box.addLayout(row)
        create_public = QPushButton("创建公网房间")
        create_public.clicked.connect(self._host_public)
        join_public = QPushButton("加入公网房间")
        join_public.clicked.connect(self._join_public)
        box.addWidget(create_public)
        box.addWidget(join_public)
        box.addWidget(QLabel("高级选项 · 局域网直连"))
        relay_row = QHBoxLayout()
        relay_row.addWidget(QLabel("Relay URL"))
        relay_row.addWidget(self.relay_url_edit)
        box.addLayout(relay_row)
        self.address = QLineEdit("127.0.0.1")
        self.address.setPlaceholderText("服务器地址 · 192.168.x.x")
        self.port_edit = QLineEdit(str(DEFAULT_GAME_PORT))
        self.port_edit.setPlaceholderText("端口")
        for label, field in (("服务器地址", self.address), ("端口", self.port_edit)):
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            row.addWidget(field)
            box.addLayout(row)
        lan_row = QHBoxLayout()
        create = QPushButton("创建局域网房间")
        create.clicked.connect(self._host)
        join = QPushButton("加入局域网房间")
        join.clicked.connect(self._join)
        lan_row.addWidget(create)
        lan_row.addWidget(join)
        box.addLayout(lan_row)
        self.connect_status = QLabel("等待连接")
        box.addWidget(self.connect_status)
        box.addStretch()
        self.pages.addWidget(page)

    def _build_lobby_page(self):
        page = QWidget()
        box = QVBoxLayout(page)
        self.lobby_title = QLabel("房间 · 五人身份局")
        box.addWidget(self.lobby_title)
        self.connection_label = QLabel("连接中")
        box.addWidget(self.connection_label)
        room_row = QHBoxLayout()
        self.room_code_label = QLabel("")
        room_row.addWidget(self.room_code_label, 1)
        copy_button = QPushButton("复制房间码")
        copy_button.clicked.connect(self._copy_room_code)
        room_row.addWidget(copy_button)
        close_button = QPushButton("关闭房间")
        close_button.clicked.connect(self.close)
        room_row.addWidget(close_button)
        box.addLayout(room_row)
        self.seat_labels = []
        self.takeover_buttons = []
        for i in range(5):
            row = QHBoxLayout()
            label = QLabel(f"座位 {i+1} · 空位")
            row.addWidget(label, 1)
            takeover = QPushButton("AI 接管")
            takeover.clicked.connect(lambda checked=False, n=i+1: self._send("TAKEOVER_AI", seat_id=f"p{n}"))
            takeover.hide()
            row.addWidget(takeover)
            box.addLayout(row)
            self.seat_labels.append(label)
            self.takeover_buttons.append(takeover)
        self.ready_button = QPushButton("准备")
        self.ready_button.clicked.connect(self._toggle_ready)
        box.addWidget(self.ready_button)
        self.start_button = QPushButton("开始游戏 · 空位补 AI")
        self.start_button.clicked.connect(lambda: self._send("START_GAME"))
        box.addWidget(self.start_button)
        self.back_to_game = QPushButton("返回对局")
        self.back_to_game.clicked.connect(lambda: self.pages.setCurrentIndex(2))
        self.back_to_game.hide()
        box.addWidget(self.back_to_game)
        self.lobby_error = QLabel("")
        box.addWidget(self.lobby_error)
        box.addStretch()
        self.pages.addWidget(page)

    def _build_game_page(self):
        page = QWidget()
        box = QVBoxLayout(page)
        self.game_status = QLabel("等待开局")
        top = QHBoxLayout()
        top.addWidget(self.game_status, 1)
        room_button = QPushButton("房间 / AI 接管")
        room_button.clicked.connect(lambda: self.pages.setCurrentIndex(1))
        top.addWidget(room_button)
        box.addLayout(top)
        self.table = GameTable()
        self.table.player_selected.connect(self._player_selected)
        self.table.shared_card_selected.connect(self._card_selected)
        box.addWidget(self.table, 1)
        self.prompt = QLabel("等待玩家行动")
        box.addWidget(self.prompt)
        self.actions_area = QScrollArea()
        self.actions_area.setWidgetResizable(True)
        self.actions_area.setFixedHeight(115)
        self.actions_widget = QWidget()
        self.actions_layout = QHBoxLayout(self.actions_widget)
        self.actions_area.setWidget(self.actions_widget)
        box.addWidget(self.actions_area)
        self.hand = HandView()
        self.hand.card_selected.connect(self._card_selected)
        box.addWidget(self.hand)
        self.pages.addWidget(page)

    def _offer_reconnect(self):
        saved = load_session()
        if not saved:
            return
        answer = QMessageBox.question(
            self, "重新连接", "检测到未完成对局，是否重新连接？"
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.relay_url_edit.setText(saved["relay_url"])
            self.room_code_edit.setText(saved["room_code"])
            self._connect_relay(saved["reconnect_token"])

    def _host_public(self):
        if self.public_host_thread or self.client_thread:
            return
        relay = self.relay_url_edit.text().strip()
        if not relay.startswith(("wss://", "ws://127.0.0.1", "ws://localhost")):
            self.connect_status.setText("生产 Relay 必须使用 wss://")
            return
        self.public_host_thread = PublicHostThread(relay, self)
        self.public_host_thread.ready.connect(self._public_host_ready)
        self.public_host_thread.failed.connect(self._public_host_failed)
        self.public_host_thread.status.connect(self._set_status)
        self.public_host_thread.start()
        self.connect_status.setText("正在创建公网房间…")

    def _public_host_ready(self, port, room_code, host_token):
        self.room_code = room_code
        self.room_code_edit.setText(room_code)
        self.room_code_label.setText(f"公网房间码：{room_code}")
        self.lobby_title.setText("公网房间 · 五人身份局")
        self._connect("127.0.0.1", port)

    def _public_host_failed(self, error):
        self.connect_status.setText(error)
        self.public_host_thread = None

    def _join_public(self):
        self._connect_relay()

    def _connect_relay(self, token=None):
        if self.client_thread:
            return
        code = self.room_code_edit.text().strip().upper()
        if len(code) < 6:
            self.connect_status.setText("请输入有效房间码")
            return
        self.room_code = code
        self.client_thread = RelayClientThread(
            self.relay_url_edit.text().strip(),
            code,
            self.name_edit.text().strip(),
            token,
            self,
        )
        self.client_thread.message.connect(self._on_message)
        self.client_thread.status.connect(self._set_status)
        self.client_thread.start()
        self.room_code_label.setText(f"公网房间码：{code}")
        self.lobby_title.setText("公网房间 · 五人身份局")
        self.pages.setCurrentIndex(1)

    def _copy_room_code(self):
        if self.room_code:
            QApplication.clipboard().setText(f"三国杀房间：{self.room_code}")

    def _host(self):
        try:
            port = int(self.port_edit.text())
            if not 1 <= port <= 65535:
                raise ValueError
        except ValueError:
            self.connect_status.setText("端口必须在 1–65535 之间")
            return
        self.server_thread = ServerThread(port, self)
        self.server_thread.listening.connect(self._host_connected)
        self.server_thread.failed.connect(self.connect_status.setText)
        self.server_thread.start()
        self.connect_status.setText("正在创建房间…")

    def _host_connected(self, port):
        self._connect("127.0.0.1", port)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
                probe.connect(("10.255.255.255", 1))
                address = probe.getsockname()[0]
        except OSError:
            address = socket.gethostbyname(socket.gethostname())
        self.lobby_title.setText(f"房间地址 · {address}:{port}")

    def _join(self):
        try:
            port = int(self.port_edit.text())
            if not 1 <= port <= 65535:
                raise ValueError
        except ValueError:
            self.connect_status.setText("端口必须在 1–65535 之间")
            return
        self._connect(self.address.text().strip(), port)

    def _connect(self, host, port):
        if self.client_thread:
            return
        self.client_thread = ClientThread(host, port, self.name_edit.text().strip(), self)
        self.client_thread.message.connect(self._on_message)
        self.client_thread.status.connect(self._set_status)
        self.client_thread.start()
        self.lobby_title.setText(f"房间地址 · {host}:{port}")
        self.pages.setCurrentIndex(1)

    def _set_status(self, status):
        self.connection_label.setText(status)
        self.connect_status.setText(status)

    def _send(self, kind, **fields):
        if self.client_thread:
            self.client_thread.send(kind, **fields)

    def _on_message(self, message):
        kind = message["type"]
        if kind == "WELCOME" and message.get("seat_id"):
            self.seat_id = message["seat_id"]
            self.host_id = message["host_id"]
        elif kind == "LOBBY_STATE":
            self.host_id = message["host_id"]
            self.room_phase = message["phase"]
            for i, seat in enumerate(message["seats"]):
                state = ("已准备" if seat["ready"] else "未准备") if seat["controller_type"] == "HUMAN" else seat["controller_type"]
                if seat["controller_type"] == "HUMAN" and not seat["connected"]:
                    state = "已断线"
                self.seat_labels[i].setText(f"座位 {i+1} · {seat['player_name'] or '空位'} · {state}")
                self.takeover_buttons[i].setVisible(self.seat_id == self.host_id and state == "已断线")
            self.ready_button.setVisible(self.seat_id is not None and self.seat_id != self.host_id and message["phase"] in ("OPEN", "READY"))
            mine = next((s for s in message["seats"] if s["seat_id"] == self.seat_id), None)
            self.ready_button.setText("取消准备" if mine and mine["ready"] else "准备")
            self.start_button.setVisible(self.seat_id == self.host_id and message["phase"] in ("OPEN", "READY"))
            self.start_button.setEnabled(all(s["ready"] or s["seat_id"] == self.host_id or s["controller_type"] != "HUMAN" for s in message["seats"]))
            self.back_to_game.setVisible(self.room_phase in ("DRAFT", "IN_GAME", "FINISHED"))
        elif kind == "DRAFT_REQUEST":
            self.pages.setCurrentIndex(2)
            self._show_draft(message)
        elif kind == "PROJECTION_UPDATE":
            self.view = deserialize_projection(message["projection"])
            self.pages.setCurrentIndex(2)
            self._render_game()
        elif kind == "PENDING_REQUEST":
            self.request = message["request"]
            self.selected.clear()
            self.remaining_ms = self.request["remaining_ms"]
            self._render_game()
        elif kind == "DECISION_RESULT":
            self.request = None
            self.selected.clear()
            self._render_game()
        elif kind == "PUBLIC_EVENT":
            self._play_public_event(message["event"])
        elif kind == "GAME_OVER":
            self.prompt.setText(f"游戏结束 · {message['result']}")
            self.request = None
            self._clear_actions()
        elif kind == "ERROR":
            self.lobby_error.setText(message.get("message", "连接错误"))
            self.prompt.setText(message.get("message", "连接错误"))

    def _toggle_ready(self):
        self._send("READY", ready=self.ready_button.text() == "准备")

    def _play_public_event(self, fact):
        kind = fact["kind"]
        if kind == 'GuhuoEvent':
            declared = GUHUO_CARD_NAMES.get(fact['declared'], fact['declared'])
            if fact['stage'] == 'reveal':
                actual = GUHUO_CARD_NAMES.get(fact['actual'], fact['actual'])
                self.table.play_public_event(f'蛊惑揭示【{actual}】 · 声明【{declared}】', '')
            else:
                self.table.play_public_event(f'蛊惑声明【{declared}】 · 扣置一张未知牌', '')
            return
        source = fact.get("source_id") or None
        target = fact.get("target_id") or None
        targets = tuple(fact.get("target_ids", ()))
        definition = fact.get("definition_id", "")
        if kind == "CardUsedEvent":
            event = CardUsedEvent("network", source, "", targets, definition)
            self.table.play_public_event(f"使用【{fact.get('card_name', '卡牌')}】", definition)
        elif kind == "TrickTargetsDeclaredEvent":
            event = TrickTargetsDeclaredEvent("network", source, "", definition, targets)
        elif kind == "CardRespondedEvent":
            event = CardRespondedEvent("network", source, "", "", definition,
                                       fact.get("response_number", 1), fact.get("response_total", 1))
        elif kind == "VirtualResponseEvent":
            event = VirtualResponseEvent("network", source, "", definition,
                                         fact.get("response_number", 1), fact.get("response_total", 1))
        elif kind == "DamageDealtEvent":
            event = DamageDealtEvent("network", source, target, fact["amount"], 0)
        elif kind == "HpRecoveredEvent":
            event = HpRecoveredEvent("network", source, target, fact["amount"], 0)
        elif kind == "PlayerDiedEvent":
            event = PlayerDiedEvent("network", target, Identity.LORD, source)
        elif kind == "GameEndedEvent":
            event = GameEndedEvent("network", fact["label"], tuple(fact["winner_ids"]))
        else:
            return
        names = {str(p.player_id): p.name for p in self.view.players} if self.view else {}
        me = next((p for p in self.view.players if p.player_id == self.seat_id), None) if self.view else None
        self.table.vfx.consume(event, definition_id=definition, human_id=self.seat_id or "",
                               names=names, identity_label=me.identity_label if me else "",
                               survivor_names=tuple(p.name for p in self.view.players if p.alive) if self.view else ())

    def _show_draft(self, message):
        self.request = message["request"]
        self.remaining_ms = self.request["remaining_ms"]
        self.game_status.setText(f"你的身份：{message['identity']} · 主公座位：{message['lord_id']}")
        self.prompt.setText("十选一 · 请选择武将")
        self._clear_actions()
        characters = {str(c.id): c for c in ALL_GENERAL_POOL}
        skills = {s.id: s for s in ALL_SKILL_CATALOGUE}
        for cid in self.request["choices"]:
            character = characters[cid]
            card = GeneralChoiceCard(character, [skills[sid].name for sid in character.skill_ids])
            card.clicked.connect(lambda checked=False, choice=cid: self._decide(choice))
            self.actions_layout.addWidget(card)
        self.actions_area.setFixedHeight(235)

    def _render_game(self):
        if self.view is None:
            return
        self.actions_area.setFixedHeight(115)
        self.table.render(self.view, set(self.request["allowed_player_ids"]) if self.request else set(), self.selected)
        self.game_status.setText(f"第 {self.view.turn_number} 回合 · {self.view.current_phase} · {self.connection_label.text()}")
        selectable = set()
        if self.request:
            selectable.update(str(x) for x in self.request["eligible_card_ids"])
            selectable.update(x[4:] for x in self.request["choices"] if x.startswith("use:"))
        self.hand.render(self.view.hand, selectable, self.selected)
        self._clear_actions()
        if not self.request:
            self.prompt.setText("等待其他玩家行动" if not self.view.result else self.view.result)
            return
        request = self.request
        self.prompt.setText(f"{request['prompt']} · {max(0, self.remaining_ms // 1000)} 秒")
        kind = request["request_type"]
        if kind == "choose_option":
            for choice in request["choices"]:
                if not choice.startswith("use:"):
                    label = ("结束出牌" if choice == END_PLAY_PHASE else
                             '蛊惑' if choice == 'skill:guhuo' else
                             f'声明【{GUHUO_CARD_NAMES[choice]}】' if choice in GUHUO_CARD_NAMES else choice)
                    self._action(label, lambda v=choice: self._decide(v))
        elif kind == "respond_with_card":
            if request["allow_pass"]:
                self._action("不出", lambda: self._decide(PASS_RESPONSE))
            for cid in request["eligible_card_ids"]:
                if str(cid).startswith("virtual:"):
                    self._action('蛊惑 · 声明响应牌' if cid == 'virtual:guhuo' else str(cid),
                                 lambda v=cid: self._decide(v))
        elif kind in ("choose_card", "choose_cards"):
            for cid in request["eligible_card_ids"]:
                card = next((item for item in self.view.hand if item.card_id == cid), None)
                label = f'{card.name} {card.suit}{card.rank}' if card else str(cid)
                self._action(label, lambda v=cid: self._card_selected(v))
            if kind == "choose_cards":
                self._action("确认选择", lambda: self._decide(tuple(self.selected)))
        elif kind == "yes_no":
            challenge = '质疑' in request['prompt']
            self._action('质疑' if challenge else "是", lambda: self._decide(True))
            self._action('不质疑' if challenge else "否", lambda: self._decide(False))
        elif kind in ("choose_player", "choose_players"):
            for pid in request["allowed_player_ids"]:
                self._action(f"座位 {pid[1:]}", lambda v=pid: self._player_selected(v))
            if kind == "choose_players":
                self._action("确认目标", lambda: self._decide(tuple(self.selected)))

    def _clear_actions(self):
        while self.actions_layout.count():
            item = self.actions_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _action(self, label, callback):
        button = QPushButton(label)
        button.clicked.connect(callback)
        self.actions_layout.addWidget(button)

    def _player_selected(self, pid):
        if not self.request or pid not in self.request["allowed_player_ids"]:
            return
        if self.request["request_type"] == "choose_player":
            self._decide(pid)
        else:
            self.selected.symmetric_difference_update({pid})
            self._render_game()

    def _card_selected(self, cid):
        if not self.request:
            return
        kind = self.request["request_type"]
        if kind == "choose_option" and f"use:{cid}" in self.request["choices"]:
            self._decide(f"use:{cid}")
        elif kind in ("choose_card", "respond_with_card") and cid in self.request["eligible_card_ids"]:
            self._decide(cid)
        elif kind == "choose_cards" and cid in self.request["eligible_card_ids"]:
            self.selected.symmetric_difference_update({cid})
            self._render_game()

    def _decide(self, value):
        if not self.request or not self.seat_id:
            return
        decision = Decision(self.request["request_id"], self.seat_id, value)
        self._send("SUBMIT_DECISION", decision=decision_to_wire(decision))

    def _countdown(self):
        if self.request and self.remaining_ms > 0:
            self.remaining_ms = max(0, self.remaining_ms - 100)
            self.prompt.setText(f"{self.request['prompt']} · {self.remaining_ms // 1000} 秒")

    def closeEvent(self, event):
        if self.client_thread:
            self.client_thread.stop()
            self.client_thread.wait(2000)
        if self.server_thread:
            self.server_thread.stop()
            self.server_thread.wait(2000)
        if self.public_host_thread:
            self.public_host_thread.stop()
            self.public_host_thread.wait(3000)
        super().closeEvent(event)


