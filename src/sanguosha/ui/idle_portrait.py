"""Native playback of the existing portrait manifest, with a static fallback."""
import json
from PySide6.QtCore import QObject, QEvent, QUrl, Signal
from PySide6.QtGui import QPixmap
from .resources import RESOURCES
try:
    from PySide6.QtMultimedia import QMediaPlayer, QVideoSink
except ImportError:
    QMediaPlayer = QVideoSink = None


class IdlePortrait(QObject):
    changed = Signal()

    def __init__(self, owner, panel=False):
        super().__init__(owner)
        self.owner, self.panel = owner, panel
        self.pixmap = None
        self.general_id = None
        self.player = None
        owner.installEventFilter(self)

    def set_general(self, general_id):
        if general_id == self.general_id:
            return
        self.general_id = general_id
        self.pixmap = None
        if self.player:
            self.player.stop()
        if QMediaPlayer is None:
            return
        try:
            manifest = json.loads((RESOURCES.root / 'idle_portraits.json').read_text(encoding='utf-8'))
            entry = manifest.get(general_id, {})
            relative = entry.get('panelVideo' if self.panel else 'video', '').removeprefix('/assets/')
            path = (RESOURCES.root / relative).resolve()
            if not relative or not path.is_relative_to(RESOURCES.root.resolve()) or not path.is_file():
                return
        except (OSError, ValueError):
            return
        if self.player is None:
            self.player = QMediaPlayer(self)
            self.sink = QVideoSink(self)
            self.player.setVideoSink(self.sink)
            self.player.setLoops(QMediaPlayer.Infinite)
            self.sink.videoFrameChanged.connect(self._frame)
        self.player.setSource(QUrl.fromLocalFile(str(path)))
        if self.owner.isVisible():
            self.player.play()

    def _frame(self, frame):
        image = frame.toImage()
        if not image.isNull():
            self.pixmap = QPixmap.fromImage(image)
            self.changed.emit()

    def eventFilter(self, watched, event):
        if self.player:
            if event.type() == QEvent.Show:
                self.player.play()
            elif event.type() in (QEvent.Hide, QEvent.Close):
                self.player.pause()
        return False
