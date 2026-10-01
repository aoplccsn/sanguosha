"""Render source-only review sheets; these are not candidate acceptance sheets."""

import json
import os
import sys
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QGuiApplication, QImage, QPainter

ROOT = Path(r"C:\Sanguosha\docs\t10_art")
ROWS = json.loads((ROOT / "v3_review" / "portrait_inventory.json").read_text(encoding="utf-8"))
QGuiApplication(sys.argv)
QFontDatabase.addApplicationFont(r"C:\Windows\Fonts\arial.ttf")
QFontDatabase.addApplicationFont(r"C:\Windows\Fonts\msyh.ttc")

for pack in ("standard", "wind", "fire", "forest", "mountain"):
    selected = [r for r in ROWS if r["pack"] == pack]
    cols = 5 if pack == "standard" else 4
    rows = (len(selected) + cols - 1) // cols
    cell_w, cell_h = 250, 370
    sheet = QImage(cols * cell_w, rows * cell_h, QImage.Format_RGB32)
    sheet.fill(QColor("#ece8dd"))
    painter = QPainter(sheet)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    painter.setPen(QColor("#172124"))
    painter.setFont(QFont("Microsoft YaHei UI", 13, QFont.Bold))
    for index, item in enumerate(selected):
        col, row = index % cols, index // cols
        path = Path(r"C:\Sanguosha") / item["snapshot_path"]
        image = QImage(str(path))
        if image.isNull():
            raise RuntimeError(f"Cannot read {path}")
        image = image.scaled(225, 315, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        x = col * cell_w + (cell_w - image.width()) // 2
        y = row * cell_h + 4
        painter.drawImage(x, y, image)
        painter.drawText(QRect(col * cell_w + 5, row * cell_h + 321, cell_w - 10, 23), Qt.AlignCenter, item["中文名"])
        painter.setFont(QFont("Arial", 9))
        painter.drawText(QRect(col * cell_w + 5, row * cell_h + 344, cell_w - 10, 18), Qt.AlignCenter, item["general_id"])
        painter.setFont(QFont("Microsoft YaHei UI", 13, QFont.Bold))
    painter.end()
    output = ROOT / "v3_review" / f"source_{pack}_sheet.png"
    if not sheet.save(str(output)):
        raise RuntimeError(f"Cannot write {output}")
    print(output)
