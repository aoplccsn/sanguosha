"""Generate original geometric placeholder artwork; safe to rerun."""
import json
import os
from pathlib import Path
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parent
app = QApplication.instance() or QApplication([])
from PySide6.QtGui import QFontDatabase
QFontDatabase.addApplicationFont("C:/Windows/Fonts/simhei.ttf")
app.setFont(QFont("Microsoft YaHei UI", 10))
manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))

def art(key, label, colors, size=(300, 390), kind="seal"):
    path = ROOT / manifest[key]
    path.parent.mkdir(parents=True, exist_ok=True)
    w, h = size
    pix = QPixmap(w, h)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    gradient = QLinearGradient(0, 0, w, h)
    gradient.setColorAt(0, QColor(colors[0]))
    gradient.setColorAt(1, QColor(colors[1]))
    painter.fillRect(pix.rect(), gradient)
    painter.setPen(QPen(QColor("#d8bd81"), max(2, w//125)))
    painter.drawRoundedRect(QRectF(10, 10, w-20, h-20), 19, 19)
    painter.drawRoundedRect(QRectF(22, 22, w-44, h-44), 15, 15)
    if kind == "portrait":
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#d4b785"))
        painter.drawEllipse(QRectF(w*.35, h*.22, w*.3, h*.24))
        painter.setBrush(QColor("#132e30"))
        painter.drawEllipse(QRectF(w*.32, h*.19, w*.36, h*.13))
        painter.drawRoundedRect(QRectF(w*.22, h*.51, w*.56, h*.39), 70, 60)
        painter.setPen(QColor("#e4c98f"))
        painter.setFont(QFont("Microsoft YaHei UI", 44, QFont.Bold))
        painter.drawText(QRectF(0, h*.68, w, 72), Qt.AlignCenter, label)
    elif kind == "table":
        painter.setPen(QPen(QColor("#a1834a"), 9))
        painter.setBrush(QColor("#153d3a"))
        painter.drawEllipse(QRectF(w*.1, h*.1, w*.8, h*.8))
        painter.setPen(QPen(QColor("#7d6947"), 3))
        painter.drawEllipse(QRectF(w*.13, h*.13, w*.74, h*.74))
    else:
        painter.setPen(QColor("#f1dfaf"))
        painter.setFont(QFont("Microsoft YaHei UI", max(24, min(w,h)//3), QFont.Bold))
        painter.drawText(pix.rect(), Qt.AlignCenter, label)
    painter.end()
    pix.save(str(path))

art("table.background", "", ("#173b37", "#0b2426"), (1440, 900), "table")
art("default.general", "将", ("#56645b", "#202b2d"), (280,360), "portrait")
for key, label, colors in [
    ("caocao","曹",("#385d77","#182b40")), ("liubei","刘",("#727b42","#263b29")),
    ("sunquan","孙",("#9a5842","#462727")), ("lvbu","吕",("#684569","#2c233a")),
    ("guanyu","关",("#487156","#233c32"))]:
    art("general."+key, label, colors, (280,360), "portrait")
art("default.basic", "牌", ("#aa9064", "#624934"))
for key, label, colors in [
    ("basic.slash","斩",("#8b383b","#40252a")),
    ("basic.dodge","影",("#39718b","#213c55")),
    ("basic.peach","桃",("#ad6d74","#506c4a"))]:
    art(key, label, colors)
for key, label, colors in [
    ("主公","主",("#a98b48","#604323")), ("忠臣","忠",("#476b8a","#263e57")),
    ("反贼","反",("#9d4944","#4d282b")), ("内奸","内",("#705a87","#342c47")),
    ("未知","?",("#4e5f5d","#243634"))]:
    art("identity."+key, label, colors, (72,72))
art("card_back", "◆", ("#6e3434", "#291f2b"), (240,340))
art("ui.button", "", ("#d3ac67", "#806039"), (240,72))
art("ui.player_frame", "", ("#435d54", "#202b2d"), (280,160))
