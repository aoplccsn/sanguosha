"""Build candidate contact sheets and record objective readiness checks."""

from __future__ import annotations

import hashlib
import json
import os
import struct
import sys
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QGuiApplication, QImage, QPainter

PROJECT = Path(r"C:\Sanguosha")
ART = PROJECT / "docs" / "t10_art"
ROWS = json.loads((ART / "v3_review" / "portrait_inventory.json").read_text(encoding="utf-8"))
QGuiApplication(sys.argv)
QFontDatabase.addApplicationFont(r"C:\Windows\Fonts\arial.ttf")


def candidate(path: Path) -> dict:
    with path.open("rb") as f:
        header = f.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise ValueError(f"Invalid PNG: {path}")
    image = QImage(str(path))
    if image.isNull():
        raise ValueError(f"Unreadable image: {path}")
    width, height = struct.unpack(">II", header[16:24])
    return {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "dimensions": [width, height], "bytes": path.stat().st_size}


def sheet(pack: str, selected: list[dict]) -> None:
    cols = 5 if pack == "standard" else 4
    rows = (len(selected) + cols - 1) // cols
    cell_w, cell_h = 250, 360
    canvas = QImage(cols * cell_w, rows * cell_h, QImage.Format_RGB32)
    canvas.fill(QColor("#e6e2d8"))
    p = QPainter(canvas)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    p.setPen(QColor("#182024"))
    p.setFont(QFont("Arial", 10))
    for i, item in enumerate(selected):
        col, row = i % cols, i // cols
        file = ART / "v3_candidates" / f"{item['general_id']}.png"
        if not file.exists():
            raise FileNotFoundError(file)
        art = QImage(str(file)).scaled(230, 320, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        x = col * cell_w + (cell_w - art.width()) // 2
        y = row * cell_h + 3
        p.drawImage(x, y, art)
        p.drawText(QRect(col * cell_w + 2, row * cell_h + 327, cell_w - 4, 22), Qt.AlignCenter, item["general_id"])
    p.end()
    out = ART / "v3_contact_sheets" / f"{pack}_sheet.png"
    if not canvas.save(str(out)):
        raise RuntimeError(f"Cannot save {out}")
    print(out)


def main() -> None:
    summary = {"total": 57, "packs": {}}
    for pack in ("standard", "wind", "fire", "forest", "mountain"):
        selected = [r for r in ROWS if r["pack"] == pack]
        ready = []
        for row in selected:
            path = ART / "v3_candidates" / f"{row['general_id']}.png"
            if path.exists():
                meta = candidate(path)
                ready.append({"general_id": row["general_id"], "candidate_path": str(path.relative_to(PROJECT)).replace("\\", "/"), **meta})
        summary["packs"][pack] = {"ready_count": len(ready), "total": len(selected), "candidates": ready}
        if len(ready) == len(selected):
            sheet(pack, selected)
    (ART / "v3_review" / "candidate_readiness.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print({pack: data["ready_count"] for pack, data in summary["packs"].items()})


if __name__ == "__main__":
    main()
