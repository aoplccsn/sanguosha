"""Five-seat felt table with a central draw/discard tableau."""
from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget
from sanguosha.projection import TableView
from .player_panel import PlayerPanel
from .resources import RESOURCES
from .theme import Theme
from .hud import PhaseIndicator

PHASES = {"preparation":"准备", "judgment":"判定", "draw":"摸牌", "play":"出牌", "discard":"弃牌", "finish":"结束"}

class GameTable(QWidget):
    player_selected = Signal(str)
    def __init__(self) -> None:
        super().__init__()
        self.phase_indicator = PhaseIndicator(self)
        self.view: TableView | None = None
        self.attack: tuple[str, str] | None = None
        self.resolving_card: str | None = None
        self._discard_card = None
        self._discard_pixmap = None
        self.panels = {f"p{i}": PlayerPanel(f"p{i}") for i in range(1, 6)}
        for panel in self.panels.values():
            panel.setParent(self)
            panel.player_selected.connect(self.player_selected)
        self.setMinimumHeight(430)

    def resizeEvent(self, event) -> None:
        w, h = self.width(), self.height()
        self.phase_indicator.setGeometry(int(w*.32), 12, int(w*.36), 32)
        pw = max(205, min(252, int(w*.21)))
        ph = max(152, min(172, int(h*.30)))
        positions = {
            "p2": (int(w*.025), int(h*.27)),
            "p3": (int(w*.24), int(h*.10)),
            "p4": (int(w*.56), int(h*.10)),
            "p5": (w-pw-int(w*.025), int(h*.27)),
            "p1": ((w-int(pw*1.28))//2, h-int(ph*1.13)-8),
        }
        for key, (x, y) in positions.items():
            self.panels[key].setGeometry(x, y, int(pw*1.28) if key == "p1" else pw, int(ph*1.13) if key == "p1" else ph)
        super().resizeEvent(event)

    def render(self, view: TableView, target_ids: set[str], selected_ids: set[str] | None = None,
               attacker_id: str | None = None, defender_id: str | None = None,
               resolving_card: str | None = None) -> None:
        self.view = view
        self.phase_indicator.phase = view.current_phase
        self.phase_indicator.update()
        self.attack = (attacker_id, defender_id) if attacker_id and defender_id else None
        self.resolving_card = resolving_card
        selected_ids = selected_ids or set()
        for player in view.players:
            pid = str(player.player_id)
            self.panels[pid].render(player, pid in target_ids, bool(target_ids), pid in selected_ids,
                                    pid == attacker_id, pid == defender_id)
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.drawPixmap(self.rect(), RESOURCES.table_background())
        w, h = self.width(), self.height()
        oval = QRectF(w*.16, h*.18, w*.68, h*.62)
        p.setBrush(QColor(10, 37, 36, 183))
        p.setPen(QPen(QColor(Theme.shade_a9854d), 7))
        p.drawEllipse(oval)
        p.setPen(QPen(QColor(221, 188, 117, 145), 2))
        p.drawEllipse(oval.adjusted(12, 12, -12, -12))
        p.setPen(QPen(QColor(221, 188, 117, 80), 1))
        p.drawEllipse(oval.adjusted(22, 22, -22, -22))
        p.setPen(QColor(Theme.shade_d9bc7c))
        p.setFont(QFont("Microsoft YaHei UI", 17, QFont.Bold))
        p.drawText(QRectF(w*.36, h*.34, w*.28, 42), Qt.AlignCenter, "五人身份局")
        p.setFont(QFont("Microsoft YaHei UI", 9))
        p.setPen(QColor(Theme.shade_a99974))
        p.drawText(QRectF(w*.38, h*.40, w*.24, 20), Qt.AlignCenter, "风云际会  ·  一局定乾坤")
        if not self.view:
            return
        v = self.view
        card_w, card_h = 76, 105
        left = int(w*.5-card_w-36)
        top = int(h*.47)
        p.drawPixmap(left, top, card_w, card_h, RESOURCES.card_back())
        if v.discard_top:
            if self._discard_card != v.discard_top:
                from .card_widget import CardWidget
                preview = CardWidget(v.discard_top)
                preview.set_selectable(True)
                self._discard_pixmap = preview.grab()
                self._discard_card = v.discard_top
                preview.deleteLater()
            p.drawPixmap(left+card_w+72, top-5, card_w, card_h+5, self._discard_pixmap)
        else:
            p.setPen(QPen(QColor(Theme.shade_998c70), 2, Qt.DashLine))
            p.setBrush(QColor(11, 25, 26, 160))
            p.drawRoundedRect(left+card_w+72, top, card_w, card_h, 6, 6)
        p.setPen(QColor(Theme.shade_ead9aa))
        p.setFont(QFont("Microsoft YaHei UI", 10))
        if not self.attack:
            p.drawText(left, top+card_h+21, f"牌堆  {v.deck_count}")
            p.drawText(left+card_w+72, top+card_h+21, f"弃牌  {v.discard_count}")
        p.setFont(QFont("Microsoft YaHei UI", 12, QFont.Bold))
        p.drawText(QRectF(w*.30, h*.73, w*.40, 32), Qt.AlignCenter, f"第 {v.turn_number} 回合    ·    {PHASES.get(v.current_phase, v.current_phase)}阶段")
        if self.attack and self.resolving_card:
            names = {str(player.player_id): player.name for player in v.players}
            source, target = self.attack
            art_rect = QRectF(w*.5-41, top-12, 82, 114)
            p.setPen(QPen(QColor(Theme.shade_ffe194), 4))
            p.setBrush(QColor(Theme.shade_42272b))
            p.drawRoundedRect(art_rect.adjusted(-4, -4, 4, 4), 7, 7)
            p.drawPixmap(art_rect.toRect(), RESOURCES.card_art(self.resolving_card))
            p.setPen(QColor(Theme.shade_ffe5ac))
            p.setFont(QFont("Microsoft YaHei UI", 11, QFont.Bold))
            p.setBrush(QColor(25, 43, 39, 225))
            banner = QRectF(w*.34, top+card_h+5, w*.32, 28)
            p.drawRoundedRect(banner, 5, 5)
            p.drawText(banner, Qt.AlignCenter,
                       f"{names.get(source, source)}  →  {names.get(target, target)}  ·  "+{'basic.fire_slash':'火杀','basic.thunder_slash':'雷杀'}.get(self.resolving_card,'杀'))
