"""Illustrated seat plaque; all data comes from the public PlayerView."""
from PySide6.QtCore import Qt, QRectF, QPoint, Signal, QVariantAnimation
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QPushButton
from sanguosha.projection import PlayerView
from .resources import RESOURCES
from .theme import Theme
from .equipment_preview import EquipmentPreview
from .card_widget import equipment_label


class PlayerPanel(QPushButton):
    player_selected = Signal(str)
    detail_requested = Signal(str)

    def __init__(self, player_id: str) -> None:
        super().__init__()
        self.player_id = player_id
        self.view: PlayerView | None = None
        self.targetable = self.selected_target = False
        self.attack_role: str | None = None
        self.pending_responder = False
        self.decision_progress: float | None = None
        self.damage_flash = self.recovery_flash = self.death_opacity = self.turn_glow = 0.0
        self._damage_animation = self._animation("damage_flash", 380)
        self._recovery_animation = self._animation("recovery_flash", 480)
        self._death_animation = self._animation("death_opacity", 420)
        self._turn_animation = self._animation("turn_glow", 280)
        self.setObjectName(f"player-{player_id}")
        self.setMinimumSize(205, 145)
        self.setMouseTracking(True)
        self._equipment_preview = EquipmentPreview(self)
        self.clicked.connect(self._activate)

    def _activate(self) -> None:
        if self.targetable:
            self.player_selected.emit(self.player_id)
        else:
            self.detail_requested.emit(self.player_id)

    def set_pending_responder(self, value: bool) -> None:
        if self.pending_responder != value:
            self.pending_responder = value
            self.update()

    def set_decision_progress(self, value: float | None) -> None:
        if self.decision_progress != value:
            self.decision_progress = value
            self.update()

    def _equipped_slots(self):
        equipment = {"武":None, "甲":None, "+1马":None, "-1马":None}
        if self.view:
            for card in self.view.equipment:
                slot = {"weapon":"武", "armor":"甲", "defensive_horse":"+1马",
                        "offensive_horse":"-1马"}.get(card.equipment_slot)
                if slot is not None:
                    equipment[slot] = card
        return equipment

    def mouseMoveEvent(self, event) -> None:
        if self.view:
            x = int(self.width()*.53)+6
            cell = (self.width()-x-11)/4
            point = event.position()
            if 98 <= point.y() <= 119 and x <= point.x() < x+cell*4:
                index = int((point.x()-x)//cell)
                card = list(self._equipped_slots().values())[index]
                if card:
                    on_right = self.mapTo(self.window(), QPoint(0, 0)).x() > self.window().width()/2
                    position = self.mapToGlobal(QPoint(-290 if on_right else self.width()+8, 0))
                    self._equipment_preview.show_card(card, position)
                    super().mouseMoveEvent(event)
                    return
        self._equipment_preview.hide()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        self._equipment_preview.hide()
        super().leaveEvent(event)

    def closeEvent(self, event) -> None:
        self._equipment_preview.hide()
        super().closeEvent(event)

    def _animation(self, attribute, duration):
        animation = QVariantAnimation(self)
        animation.setDuration(duration)
        animation.valueChanged.connect(lambda value: (setattr(self, attribute, float(value)), self.update()))
        return animation

    def _start_animation(self, animation, start, end):
        animation.stop()
        animation.setStartValue(float(start))
        animation.setEndValue(float(end))
        animation.start()

    def render(self, view: PlayerView, targetable: bool, choosing_target: bool,
               selected_target: bool = False, attacker: bool = False, defender: bool = False) -> None:
        old = self.view
        if old and view.hp < old.hp:
            self._start_animation(self._damage_animation, 1, 0)
        if old and view.hp > old.hp:
            self._start_animation(self._recovery_animation, 1, 0)
        if old and old.alive and not view.alive:
            self._start_animation(self._death_animation, 0, 1)
        elif old is None or not old.alive and view.alive:
            self._death_animation.stop()
            self.death_opacity = 0 if view.alive else 1
        if old is None or old.active != view.active:
            self._turn_animation.stop()
            if view.active:
                self._turn_animation.setDuration(1600)
                self._turn_animation.setKeyValues([(0, 0.4), (0.5, 1.0), (1, 0.4)])
                self._turn_animation.setLoopCount(-1)
                self._turn_animation.start()
            else:
                self.turn_glow = 0
        self.view = view
        self.targetable = targetable
        self.selected_target = selected_target
        self.attack_role = "attacker" if attacker else "defender" if defender else None
        status = "阵亡" if not view.alive else "当前回合" if view.active else "存活"
        self.setText(f"{view.name} · {view.character_name} {view.identity_label} {status} 手牌 {view.hand_count}")
        distance_text = (f"\n距离：{view.base_distance}；装备修正后：{view.effective_distance}"
                         if view.base_distance is not None else "")
        buqu = view.special_piles.get('buqu', ())
        buqu_text = ("\n不屈牌：" + "、".join(card.suit + card.rank for card in buqu)) if buqu else ""
        committed = tuple(card for key, cards in view.special_piles.items()
                          if key.startswith('committed:') for card in cards)
        committed_text = ("\n蛊惑扣牌：" + "、".join(card.name for card in committed)) if committed else ""
        abolished_names={'weapon':'武器栏','armor':'防具栏','offensive_horse':'进攻马栏','defensive_horse':'防御马栏'}
        abolished_text=("\n已废除："+"、".join(abolished_names[slot] for slot in view.abolished_equipment_slots)) if view.abolished_equipment_slots else ""
        counters=view.special_piles.get('counter',())
        counter_text=("\n逆："+"、".join(card.name+card.suit+card.rank for card in counters)) if counters else ""
        self.setToolTip("装备：" + ("、".join(c.name for c in view.equipment) or "无") +
                        "\n判定：" + ("、".join(c.name for c in view.judgments) or "无") +
                        f"\n当前攻击范围：{view.attack_range}" + distance_text + buqu_text + committed_text + abolished_text + counter_text)
        self.setEnabled(not choosing_target or targetable)
        self.setCursor(Qt.PointingHandCursor if targetable else Qt.ArrowCursor)
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        outer = QRectF(3, 3, w-6, h-6)
        edge = QColor(Theme.selected if self.selected_target else
                      "#f4cb65" if self.view and self.view.active else
                      "#e0bc69" if self.targetable else
                      "#b35a43" if self.attack_role == "attacker" else
                      "#668a98" if self.attack_role == "defender" else
                      "#8b7053")
        if self.selected_target or self.targetable or self.attack_role or self.turn_glow or self.pending_responder:
            halo = QColor(edge)
            halo.setAlpha(110 if self.selected_target else 45 + int(35*self.turn_glow))
            p.setPen(QPen(halo, 6))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(outer, 8, 8)
        grad = QLinearGradient(0, 0, w, h)
        grad.setColorAt(0, QColor("#ede0c4"))
        grad.setColorAt(1, QColor("#b9a384"))
        p.setBrush(grad)
        p.setPen(QPen(edge, 4 if self.selected_target else 2))
        p.drawRoundedRect(outer, 7, 7)
        if self.view and self.view.active:
            gold = QColor("#f6d47d")
            gold.setAlpha(175 + int(70 * self.turn_glow))
            p.setPen(QPen(gold, 5))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(outer.adjusted(2, 2, -2, -2), 7, 7)
        if self.pending_responder:
            p.setPen(QPen(QColor("#ffb65b"), 3))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(outer.adjusted(7, 7, -7, -7), 5, 5)
        p.setPen(QPen(QColor("#5c402b"), 1))
        p.drawRoundedRect(outer.adjusted(5, 5, -5, -5), 4, 4)
        if not self.view:
            return
        v = self.view
        portrait_width = int(w*.53)
        art = QRectF(9, 9, portrait_width-8, h-18)
        clip = QPainterPath()
        clip.addRoundedRect(art, 3, 3)
        p.setClipPath(clip)
        portrait = RESOURCES.general_portrait(v.character_id, v.character_name)
        portrait_box = art.toRect()
        scaled = portrait.scaled(portrait_box.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        crop_x = (scaled.width() - portrait_box.width()) // 2
        # Keep the face near the upper edge visible in the compact seat plaque.
        p.drawPixmap(portrait_box, scaled.copy(crop_x, 0, portrait_box.width(), portrait_box.height()))
        if not v.face_up:
            p.fillRect(art, QColor(20, 16, 13, 145))
            p.setPen(QColor("#f0d18c"))
            p.setFont(QFont("Microsoft YaHei UI", 10, QFont.Bold))
            p.drawText(art, Qt.AlignCenter, "翻面")
        if not v.alive:
            p.fillRect(art, QColor(24, 21, 19, int(185*self.death_opacity)))
        buqu = v.special_piles.get('buqu', ())
        field_cards = v.special_piles.get('tian', ())
        committed = tuple(card for key, cards in v.special_piles.items()
                          if key.startswith('committed:') for card in cards)
        if buqu or committed or field_cards or v.active_transformation:
            badge = QRectF(art.left(), art.bottom()-21, art.width(), 20)
            p.fillRect(badge, QColor(30, 24, 19, 190))
            p.setPen(QColor("#f4d58b"))
            p.setFont(QFont("Microsoft YaHei UI", 7, QFont.Bold))
            p.drawText(badge, Qt.AlignCenter,
                       ("不屈 " + str(len(buqu)) + " · " + " ".join(card.rank for card in buqu))
                       if buqu else "田 " + str(len(field_cards)) if field_cards
                       else "化身 " + v.active_transformation if v.active_transformation
                       else "蛊惑 · " + committed[0].name)
        p.setClipping(False)
        p.setPen(QPen(QColor("#795d3c"), 2))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(art, 3, 3)
        x = portrait_width + 6
        rw = w-x-11
        p.setPen(QColor("#2e2821"))
        p.setFont(QFont("Microsoft YaHei UI", 12, QFont.Bold))
        p.drawText(QRectF(x, 12, rw-25, 23), Qt.AlignLeft, v.character_name)
        p.drawPixmap(w-34, 9, 25, 25, RESOURCES.identity_icon(v.identity_label))
        p.setPen(QColor("#f6e8c8"))
        p.setFont(QFont("Microsoft YaHei UI", 9, QFont.Bold))
        seal = {"主公":"主", "忠臣":"忠", "反贼":"反", "内奸":"内", "未知":"?"}.get(v.identity_label, "?")
        p.drawText(QRectF(w-34, 9, 25, 25), Qt.AlignCenter, seal)
        faction_color = {"魏":"#435a73", "蜀":"#765438", "吴":"#55725f", "群":"#685b67"}.get(v.faction, "#685b67")
        p.setBrush(QColor(faction_color))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(x, 37, 26, 20), 3, 3)
        p.setPen(QColor("#f8edda"))
        p.setFont(QFont("Microsoft YaHei UI", 9, QFont.Bold))
        p.drawText(QRectF(x, 37, 26, 20), Qt.AlignCenter, v.faction)
        p.setPen(QColor("#4b3c2c"))
        p.drawText(QRectF(x+30, 37, rw-30, 20), Qt.AlignLeft, v.name)
        bead_step = min(19, max(12, (rw-8)//max(1, v.max_hp)))
        for i in range(v.max_hp):
            cx = x+7+i*bead_step
            bead = QLinearGradient(cx-6, 61, cx+6, 74)
            bead.setColorAt(0, QColor("#e4a97a" if i < v.hp else "#aaa18f"))
            bead.setColorAt(1, QColor("#9c3d37" if i < v.hp else "#665b50"))
            p.setBrush(bead)
            p.setPen(QPen(QColor("#efcf91" if i < v.hp else "#81715d"), 1))
            p.drawEllipse(QRectF(cx-6, 61, 13, 13))
        p.setPen(QColor("#493b2d"))
        p.setFont(QFont("Microsoft YaHei UI", 8))
        p.drawText(QRectF(x, 78, rw, 17), Qt.AlignLeft, f"手牌 {v.hand_count}   体力 {v.hp}/{v.max_hp}")
        if v.skill_labels:
            p.setFont(QFont("Microsoft YaHei UI", 7, QFont.Bold))
            p.setPen(QColor("#6e4229"))
            p.drawText(QRectF(11, h-38, int(w*.52)-12, 28), Qt.TextWordWrap,
                       " · ".join(v.skill_labels))
        equipment = self._equipped_slots()
        cell = rw/4
        for i, (slot, card) in enumerate(equipment.items()):
            abolished={'武':'weapon','甲':'armor','+1马':'defensive_horse','-1马':'offensive_horse'}[slot] in v.abolished_equipment_slots
            box = QRectF(x+i*cell, 98, cell-2, 21)
            p.setBrush(QColor("#8e6963" if abolished else "#e2d0ab" if card else "#b3a084"))
            p.setPen(QPen(QColor("#8a6c48"), 1))
            p.drawRoundedRect(box, 2, 2)
            p.setPen(QColor("#3b3027" if card else "#756653"))
            p.setFont(QFont("Microsoft YaHei UI", 7, QFont.Bold if card else QFont.Normal))
            p.drawText(box, Qt.AlignCenter, "废"+slot if abolished else equipment_label(card, compact=True) if card else slot)
        p.setPen(QColor("#624b34"))
        if v.judgments:
            step = min(31, (rw*.72)/max(1, len(v.judgments)))
            for i, card in enumerate(v.judgments[:3]):
                jx = x+i*step
                p.setPen(QPen(QColor("#8b6841"), 1))
                p.setBrush(QColor("#e7d7b9"))
                p.drawRoundedRect(QRectF(jx, 122, 18, 25), 2, 2)
                p.drawPixmap(int(jx+2), 124, 14, 17, RESOURCES.card_art(card.definition_id))
                p.setPen(QColor("#3f3026"))
                p.setFont(QFont("Microsoft YaHei UI", 6))
                p.drawText(QRectF(jx-4, 140, 26, 9), Qt.AlignCenter, card.name[:2])
        else:
            p.setFont(QFont("Microsoft YaHei UI", 8))
            p.drawText(QRectF(x, 121, rw, 18), Qt.AlignLeft, "判定 · 无")
        p.setFont(QFont("Microsoft YaHei UI", 8, QFont.Bold))
        p.setPen(QColor("#8b3f31" if v.chained else "#756653"))
        p.drawText(QRectF(x, h-25, rw, 17), Qt.AlignRight, "连环" if v.chained else "当前回合" if v.active else "")
        if v.chained:
            p.setPen(QPen(QColor("#8b3f31"), 2))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QRectF(w-57, h-22, 12, 9))
            p.drawEllipse(QRectF(w-50, h-22, 12, 9))
        if v.marks:
            p.setPen(QColor("#f0d18c"))
            p.setFont(QFont("Microsoft YaHei UI", 7, QFont.Bold))
            names={'qiaoshui_success':'巧说待用','qiaoshui_trick_lock':'巧说禁锦囊','zhuikong_self_only':'惴恐限自身','junlve':'军略','zhanhuo_used':'绽火已用','longnu_form':'龙怒形态','longnu_next':'下次龙怒','poxi_hand_limit':'魄袭减上限','camp':'营','wine':'酒','quan':'权','zili_awakened':'自立已觉醒'}
            marks = "  ".join(f"{names.get(key,'标记')} {value}" for key, value in v.marks.items() if value)
            if marks:
                p.drawText(QRectF(x, h-42, rw, 14), Qt.AlignRight, marks)
        if v.active:
            p.setPen(QPen(QColor("#b88d43"), 3))
            p.drawLine(10, h-8, w-10, h-8)
        if self.decision_progress is not None:
            fraction = max(0.0, min(1.0, self.decision_progress))
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#61503b"))
            p.drawRoundedRect(QRectF(12, h-13, w-24, 6), 3, 3)
            p.setBrush(QColor("#d99153" if fraction < .2 else "#e4bf6f"))
            p.drawRoundedRect(QRectF(12, h-13, (w-24)*fraction, 6), 3, 3)
        if self.attack_role:
            p.setBrush(QColor("#913f31" if self.attack_role == "attacker" else "#456d7a"))
            p.setPen(QColor("#f6e6c4"))
            badge = QRectF(13, 14, 39, 19)
            p.drawRoundedRect(badge, 3, 3)
            p.drawText(badge, Qt.AlignCenter, "出杀" if self.attack_role == "attacker" else "受击")
        if self.damage_flash:
            p.fillRect(outer, QColor(180, 43, 33, int(125*self.damage_flash)))
        if self.recovery_flash:
            p.fillRect(outer, QColor(103, 151, 91, int(100*self.recovery_flash)))
        if not v.alive:
            p.setPen(QColor("#a23831"))
            p.setFont(QFont("Microsoft YaHei UI", 18, QFont.Bold))
            p.drawText(art, Qt.AlignCenter, "阵亡")
