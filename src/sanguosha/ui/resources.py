"""Stable asset IDs, live file replacement and self-contained fallback artwork."""
import json
import hashlib
from pathlib import Path
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPixmap
ASSETS = Path(__file__).resolve().parents[3] / "assets"

class ResourceManager:
    def __init__(self, root=None):
        self.root = Path(root) if root else ASSETS
        self._cache = {}
        self.reload()

    def reload(self):
        """Reload an edited manifest; artwork file replacements are detected automatically."""
        try:
            self.manifest = json.loads((self.root / "manifest.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.manifest = {}
        self._cache.clear()

    def _path(self, key):
        path = (self.root / self.manifest.get(key, "__missing__")).resolve()
        return path if path.is_relative_to(self.root.resolve()) else self.root / "__missing__"

    def _get(self, key, size, fallback="default.card"):
        candidates = (self._path(key), self._path(fallback))
        stamp = tuple((str(p), p.stat().st_mtime_ns, p.stat().st_size) if p.is_file() else (str(p),) for p in candidates)
        cached = self._cache.get((key, size))
        if cached and cached[0] == stamp:
            return cached[1]
        pix = QPixmap()
        for path in candidates:
            if path.is_file():
                pix = QPixmap(str(path))
                if not pix.isNull():
                    break
        if pix.isNull():
            pix = self._generated("将" if key.startswith("general.") else "牌", size)
        else:
            pix = pix.scaled(*size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            pix = pix.copy((pix.width()-size[0])//2, (pix.height()-size[1])//2, *size)
        self._cache[(key, size)] = (stamp, pix)
        return pix

    def general_portrait(self, general_id, name=""):
        key = general_id if general_id.startswith("general.") else f"general.{general_id}"
        pix = self._get(key, (280, 360), "default.general")
        if not self._path(key).is_file() or QPixmap(str(self._path(key))).isNull():
            pix = pix.copy()
            p = QPainter(pix)
            # Identity remains visible even when the selected font has no CJK glyphs.
            signature = hashlib.sha256((key + "\0" + name).encode("utf-8")).digest()
            p.setPen(Qt.NoPen)
            for index, value in enumerate(signature[:12]):
                p.setBrush(QColor(60 + value // 2, 80 + signature[index + 12] // 2, 70 + signature[index + 16] // 2))
                p.drawRect(18 + (index % 4) * 60, 25 + (index // 4) * 40, 42, 25)
            p.fillRect(QRectF(8, 287, 264, 64), QColor(10, 25, 27, 210))
            p.setPen(QColor("#f4e4bb"))
            p.setFont(QFont("Microsoft YaHei UI", 22, QFont.Bold))
            p.drawText(QRectF(12, 290, 256, 58), Qt.AlignCenter, name or general_id)
            p.end()
        return pix

    def card_art(self, card_definition_id):
        return self._get(card_definition_id, (300, 390))

    def identity_icon(self, identity):
        aliases = {"主公":"lord", "忠臣":"loyalist", "反贼":"rebel", "内奸":"renegade", "未知":"hidden"}
        identity = getattr(identity, "value", identity)
        return self._get(f"identity.{aliases.get(identity, identity)}", (72, 72), "identity.hidden")

    def card_back(self):
        return self._get("card_back", (240, 340))

    def table_background(self):
        return self._get("table.background", (1440, 900), "default.table")

    def ui_icon(self, name):
        return self._get(f"ui.{name}", (72, 72), "ui.player_frame")

    def _generated(self, label, size):
        pix = QPixmap(*size)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        grad = QLinearGradient(0, 0, size[0], size[1])
        grad.setColorAt(0, QColor("#375952"))
        grad.setColorAt(1, QColor("#15292e"))
        p.fillRect(pix.rect(), grad)
        p.setPen(QColor("#d7bd82"))
        p.drawRoundedRect(QRectF(9, 9, size[0]-18, size[1]-18), 16, 16)
        p.setFont(QFont("Microsoft YaHei UI", max(18, min(size)//5), QFont.Bold))
        p.drawText(pix.rect(), Qt.AlignCenter, label)
        p.end()
        return pix

RESOURCES = ResourceManager()

