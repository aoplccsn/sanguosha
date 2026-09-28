"""Generate original non-illustration resources. No network or commercial artwork."""
import os
import json
import math
import random
from pathlib import Path
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QFont, QLinearGradient, QPainterPath

ROOT = Path(__file__).resolve().parents[1] / "assets"

def save(path, size, draw):
    image = QImage(*size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    p = QPainter(image)
    p.setRenderHint(QPainter.Antialiasing)
    draw(p, *size)
    p.end()
    destination = ROOT / path
    destination.parent.mkdir(parents=True, exist_ok=True)
    assert image.save(str(destination))

def table(p, w, h):
    g = QLinearGradient(0, 0, w, h)
    g.setColorAt(0, QColor("#214741"))
    g.setColorAt(1, QColor("#081f24"))
    p.fillRect(0, 0, w, h, g)
    rng = random.Random(51)
    p.setPen(QColor(183, 197, 153, 14))
    for i in range(12000):
        x, y = rng.randrange(w), rng.randrange(h)
        p.drawLine(x, y, x+2, y)
    p.setPen(QPen(QColor("#735936"), 12))
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(QRectF(10, 10, w-20, h-20), 30, 30)
    p.setPen(QPen(QColor("#b99a60"), 2))
    p.drawRoundedRect(QRectF(21, 21, w-42, h-42), 22, 22)

def back(p, w, h):
    g = QLinearGradient(0, 0, w, h)
    g.setColorAt(0, QColor("#53303c"))
    g.setColorAt(1, QColor("#142e35"))
    p.fillRect(0, 0, w, h, g)
    p.setPen(QPen(QColor("#c8a36b"), 3))
    p.setBrush(Qt.NoBrush)
    for inset in (10, 18):
        p.drawRoundedRect(QRectF(inset, inset, w-2*inset, h-2*inset), 13, 13)
    p.setPen(QPen(QColor(202, 174, 104, 55), 1))
    for x in range(-h, w+h, 20):
        p.drawLine(x, 20, x+h, h-20)
        p.drawLine(x, h-20, x+h, 20)
    p.setBrush(QColor("#21383a"))
    p.setPen(QPen(QColor("#d8b97b"), 3))
    p.drawEllipse(QRectF(w*.18, h*.27, w*.64, w*.64))
    p.setFont(QFont("Microsoft YaHei UI", 35, QFont.Bold))
    p.setPen(QColor("#e5cca1"))
    p.drawText(QRectF(0, h*.30, w, w*.5), Qt.AlignCenter, "策")

def seal(label, color):
    def draw(p, w, h):
        p.setPen(QPen(QColor("#e4c993"), 5))
        p.setBrush(QColor(color))
        p.drawRoundedRect(QRectF(8, 8, w-16, h-16), 18, 18)
        p.setPen(QPen(QColor("#e4c993"), 1.5))
        p.drawRoundedRect(QRectF(17, 17, w-34, h-34), 12, 12)
        p.setFont(QFont("Microsoft YaHei UI", 48, QFont.Bold))
        p.drawText(QRectF(8, 8, w-16, h-16), Qt.AlignCenter, label)
    return draw

def frame(p, w, h):
    p.setBrush(QColor("#1c3936"))
    p.setPen(QPen(QColor("#b89861"), 5))
    p.drawRoundedRect(QRectF(4, 4, w-8, h-8), 15, 15)

def button(p, w, h):
    g = QLinearGradient(0, 0, 0, h)
    g.setColorAt(0, QColor("#89683e"))
    g.setColorAt(1, QColor("#42341e"))
    p.setBrush(g)
    p.setPen(QPen(QColor("#cba76c"), 3))
    p.drawRoundedRect(QRectF(3, 3, w-6, h-6), 9, 9)

def hp(p, w, h):
    p.setBrush(QColor("#bb4d45"))
    p.setPen(QPen(QColor("#f2ce91"), 3))
    p.drawEllipse(QRectF(8, 8, w-16, h-16))

def main():
    app = QApplication.instance() or QApplication([])
    manifest_path = ROOT / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "default.card":"cards/default_card.png",
        "default.trick":"cards/default_card.png",
        "default.delayed_trick":"cards/default_card.png",
        "default.equipment":"cards/default_card.png",
        "default.table":"backgrounds/table/felt.png",
        "ui.hp":"icons/hp.png",
    })
    for key, label, color in (
        ("lord", "主", "#8b5733"), ("loyalist", "忠", "#3f677a"),
        ("rebel", "反", "#8f383c"), ("renegade", "内", "#695276"),
        ("hidden", "?", "#334d49"),
    ):
        path = f"identities/{key}.png"
        manifest[f"identity.{key}"] = path
        save(path, (144, 144), seal(label, color))
    save("backgrounds/table/felt.png", (1440, 900), table)
    save("card_backs/default.png", (240, 340), back)
    save("ui/frames/player.png", (320, 180), frame)
    save("ui/buttons/primary.png", (240, 72), button)
    save("icons/hp.png", (72, 72), hp)
    for folder in ("cards/trick", "cards/delayed_trick", "cards/equipment", "suits", "effects", "ui/phase", "ui/status", "backgrounds/panels"):
        directory = ROOT / folder
        directory.mkdir(parents=True, exist_ok=True)
        (directory / ".gitkeep").touch()
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

if __name__ == "__main__":
    main()
