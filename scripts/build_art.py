"""Rebuild deployable art from the original illustrations in assets/source_art."""
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QFont, QFontDatabase, QImage, QPainter, QPen
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1] / "assets"
SOURCE = ROOT / "source_art"


def crop_image(source: Path, target: Path, size: tuple[int, int]) -> None:
    image = QImage(str(source))
    assert not image.isNull(), source
    image = image.scaled(*size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    x, y = (image.width() - size[0]) // 2, (image.height() - size[1]) // 2
    target.parent.mkdir(parents=True, exist_ok=True)
    assert image.copy(x, y, *size).save(str(target)), target


def seal(label: str, target: Path, color: str) -> None:
    image = QImage(144, 144, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    p = QPainter(image)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(QColor("#e6c88d"), 5))
    p.setBrush(QColor(color))
    p.drawRoundedRect(QRectF(9, 9, 126, 126), 20, 20)
    p.setPen(QPen(QColor("#f4dfb3"), 2))
    p.drawRoundedRect(QRectF(17, 17, 110, 110), 15, 15)
    p.setFont(QFont("Microsoft YaHei UI", 31, QFont.Bold))
    p.drawText(QRectF(18, 18, 108, 108), Qt.AlignCenter, label)
    p.end()
    target.parent.mkdir(parents=True, exist_ok=True)
    assert image.save(str(target))


if __name__ == "__main__":
    app = QApplication.instance() or QApplication([])
    QFontDatabase.addApplicationFont("C:/Windows/Fonts/simhei.ttf")
    portraits = {
        "caocao": "generals/wei/caocao.png",
        "liubei": "generals/shu/liubei.png",
        "sunquan": "generals/wu/sunquan.png",
        "lvbu": "generals/qun/lvbu.png",
        "guanyu": "generals/shu/guanyu.png",
        "default_general": "generals/default_general.png",
    }
    for name, path in portraits.items():
        crop_image(SOURCE / f"{name}.png", ROOT / path, (560, 720))
    for name in ("slash", "dodge", "peach"):
        crop_image(SOURCE / f"{name}.png", ROOT / "cards" / "basic" / f"{name}.png", (480, 560))
    for name, label, color in (
        ("lord", "主公", "#83502f"),
        ("loyalist", "忠臣", "#435e64"),
        ("rebel", "反贼", "#783b3d"),
        ("renegade", "内奸", "#53515b"),
        ("hidden", "未知", "#4b5a52"),
    ):
        seal(label, ROOT / "identities" / f"{name}.png", color)
