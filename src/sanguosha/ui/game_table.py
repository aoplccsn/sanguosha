"""Five seats around a quiet ink-wash resolution area."""
from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget
from sanguosha.projection import TableView
from .player_panel import PlayerPanel
from .resources import RESOURCES
from .hud import PhaseIndicator

PHASES = {"preparation":"准备", "judgment":"判定", "draw":"摸牌",
          "play":"出牌", "discard":"弃牌", "finish":"结束"}


class GameTable(QWidget):
    player_selected = Signal(str)
    shared_card_selected = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.phase_indicator = PhaseIndicator(self)
        self.view: TableView | None = None
        self.attack: tuple[str, str] | None = None
        self.resolving_card: str | None = None
        self.center_notice: str | None = None
        self.center_art: str | None = None
        self._discard_card = self._discard_pixmap = None
        self.selected_shared_id: str | None = None
        self._shared_rects: dict[str, QRectF] = {}
        self.panels = {f"p{i}": PlayerPanel(f"p{i}") for i in range(1, 6)}
        for panel in self.panels.values():
            panel.setParent(self)
            panel.player_selected.connect(self.player_selected)
        self.setMinimumHeight(400)

    def resizeEvent(self, event) -> None:
        w, h = self.width(), self.height()
        self.phase_indicator.setGeometry(int(w*.35), 5, int(w*.30), 27)
        pw = max(205, min(300, int(w*.18)))
        ph = max(148, min(205, int(h*.34)))
        positions = {
            "p2": (int(w*.018), int(h*.30)),
            "p3": (int(w*.225), int(h*.085)),
            "p4": (w-int(w*.225)-pw, int(h*.085)),
            "p5": (w-pw-int(w*.018), int(h*.30)),
            "p1": ((w-int(pw*1.19))//2, h-int(ph*1.05)-5),
        }
        for key, (x, y) in positions.items():
            width = int(pw*1.19) if key == "p1" else pw
            height = int(ph*1.05) if key == "p1" else ph
            self.panels[key].setGeometry(x, y, width, height)
        super().resizeEvent(event)

    def render(self, view: TableView, target_ids: set[str], selected_ids: set[str] | None = None,
               attacker_id: str | None = None, defender_id: str | None = None,
               resolving_card: str | None = None, selected_shared_id: str | None = None,
               center_notice: str | None = None, center_art: str | None = None) -> None:
        self.view = view
        self.phase_indicator.phase = view.current_phase
        self.phase_indicator.update()
        self.attack = (attacker_id, defender_id) if attacker_id and defender_id else None
        self.resolving_card = resolving_card
        self.center_notice = center_notice
        self.center_art = center_art
        self.selected_shared_id = selected_shared_id
        selected_ids = selected_ids or set()
        for player in view.players:
            pid = str(player.player_id)
            self.panels[pid].render(player, pid in target_ids, bool(target_ids), pid in selected_ids,
                                    pid == attacker_id, pid == defender_id)
        self.update()

    def mousePressEvent(self, event) -> None:
        for cid, rect in self._shared_rects.items():
            if rect.contains(event.position()):
                self.shared_card_selected.emit(cid)
                return
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.drawPixmap(self.rect(), RESOURCES.table_background())
        if not self.view:
            return
        v = self.view
        w, h = self.width(), self.height()
        center_y = int(h*.39)
        self._shared_rects = {}
        p.setFont(QFont("Microsoft YaHei UI", 10, QFont.Bold))
        p.setPen(QColor("#60442e"))
        p.drawText(QRectF(w*.39, center_y-31, w*.22, 22), Qt.AlignCenter,
                   "交锋 · 结算" if self.attack else "牌局 · 桌心")
        if self.attack and self.resolving_card:
            names = {str(player.player_id): player.name for player in v.players}
            source, target = self.attack
            art = QRectF(w*.5-39, center_y-7, 78, 102)
            p.setBrush(QColor("#f2e4bd"))
            p.setPen(QPen(QColor("#ad7d39"), 4))
            p.drawRoundedRect(art.adjusted(-5, -5, 5, 5), 5, 5)
            p.drawPixmap(art.toRect(), RESOURCES.card_art(self.resolving_card))
            p.setFont(QFont("Microsoft YaHei UI", 10, QFont.Bold))
            p.setPen(QColor("#713e2c"))
            p.drawText(QRectF(w*.27, center_y-54, w*.46, 27), Qt.AlignCenter,
                       f"{names.get(source, source)}  →  【杀】  →  {names.get(target, target)}")
        elif self.center_notice:
            art = QRectF(w*.5-32, center_y-12, 64, 87)
            p.setPen(QPen(QColor("#af8348"), 3))
            p.setBrush(QColor("#e8d4ab"))
            p.drawRoundedRect(art.adjusted(-4, -4, 4, 4), 4, 4)
            p.drawPixmap(art.toRect(), RESOURCES.card_art(self.center_art or "default.card"))
            p.setPen(QColor("#573b28"))
            p.setFont(QFont("Microsoft YaHei UI", 9, QFont.Bold))
            p.drawText(QRectF(w*.32, center_y+80, w*.36, 55),
                       Qt.AlignCenter | Qt.TextWordWrap, self.center_notice)
        elif v.shared_cards:
            cards = v.shared_cards[:7]
            card_w, gap = 54, 8
            start = (w - (len(cards)*card_w+(len(cards)-1)*gap))/2
            for i, card in enumerate(cards):
                x = int(start+i*(card_w+gap))
                rect = QRectF(x-3, center_y-3, card_w+6, 79)
                self._shared_rects[str(card.card_id)] = rect
                if str(card.card_id) == self.selected_shared_id:
                    p.setPen(QPen(QColor("#e7bd62"), 4))
                    p.setBrush(QColor("#fff1cf"))
                    p.drawRoundedRect(rect, 5, 5)
                p.drawPixmap(x, center_y, card_w, 73, RESOURCES.card_art(card.definition_id))
                p.setPen(QColor("#442f21"))
                p.setFont(QFont("Microsoft YaHei UI", 8, QFont.Bold))
                p.drawText(QRectF(x-3, center_y+74, card_w+6, 20), Qt.AlignCenter, card.name)
        else:
            left = int(w*.5-77)
            card_w, card_h = 54, 76
            p.drawPixmap(left, center_y, card_w, card_h, RESOURCES.card_back())
            if v.discard_top:
                p.drawPixmap(left+101, center_y, card_w, card_h,
                             RESOURCES.card_art(v.discard_top.definition_id))
            else:
                p.setPen(QPen(QColor("#8d7858"), 1, Qt.DashLine))
                p.setBrush(QColor(230, 217, 190, 100))
                p.drawRoundedRect(left+101, center_y, card_w, card_h, 3, 3)
            p.setPen(QColor("#5c422d"))
            p.setFont(QFont("Microsoft YaHei UI", 8, QFont.Bold))
            p.drawText(QRectF(left-7, center_y+78, 69, 18), Qt.AlignCenter, f"牌堆 {v.deck_count}")
            p.drawText(QRectF(left+94, center_y+78, 69, 18), Qt.AlignCenter, f"弃牌 {v.discard_count}")
