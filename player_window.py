import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSlider, QFileDialog
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import Qt, QUrl, QTimer
from PySide6.QtGui import QFont


def fmt_time(ms: int) -> str:
    s = ms // 1000
    m, s = divmod(s, 60)
    return f"{m}m {s}s"


class PlayerWindow(QDialog):
    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.setWindowTitle(f"{os.path.basename(file_path)} - BarsikTune")
        self.setMinimumWidth(380)
        self.setFixedHeight(210)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowTitleHint
        )

        # --- Media ---
        self.player = QMediaPlayer(self)
        self.audio_out = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_out)
        self.audio_out.setVolume(1.0)
        self.player.setSource(QUrl.fromLocalFile(file_path))
        self.player.play()

        self.player.durationChanged.connect(self._on_duration)
        self.player.positionChanged.connect(self._on_position)
        self.player.playbackStateChanged.connect(self._on_state)

        self._seeking = False

        # --- UI ---
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(10)

        lbl_header = QLabel("Проигрывание музыки:")
        bold = QFont()
        bold.setBold(True)
        lbl_header.setFont(bold)
        layout.addWidget(lbl_header)

        self.lbl_track = QLabel(os.path.basename(file_path))
        self.lbl_track.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_track)

        # Progress row
        prog_row = QHBoxLayout()
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.sliderPressed.connect(self._seek_start)
        self.slider.sliderReleased.connect(self._seek_end)
        self.lbl_time = QLabel("0m 0s / 0m 0s")
        prog_row.addWidget(self.slider, 1)
        prog_row.addWidget(self.lbl_time)
        layout.addLayout(prog_row)

        layout.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.btn_playpause = QPushButton("Пауза")
        self.btn_playpause.setFixedWidth(110)
        self.btn_playpause.clicked.connect(self._toggle_play)

        btn_change = QPushButton("Сменить...")
        btn_change.setFixedWidth(100)
        btn_change.clicked.connect(self._change_file)

        btn_cancel = QPushButton("Отмена")
        btn_cancel.setFixedWidth(80)
        btn_cancel.clicked.connect(self.close)

        btn_row.addWidget(self.btn_playpause)
        btn_row.addWidget(btn_change)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

    def _on_duration(self, duration: int):
        self.slider.setRange(0, duration)
        self._update_time_label(self.player.position(), duration)

    def _on_position(self, position: int):
        if not self._seeking:
            self.slider.setValue(position)
        self._update_time_label(position, self.player.duration())

    def _update_time_label(self, pos: int, dur: int):
        self.lbl_time.setText(f"{fmt_time(pos)} / {fmt_time(dur)}")

    def _on_state(self, state):
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        self.btn_playpause.setText("Пауза" if playing else "Играть")

    def _toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def _seek_start(self):
        self._seeking = True

    def _seek_end(self):
        self._seeking = False
        self.player.setPosition(self.slider.value())

    def _change_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Сменить файл", "", "Аудио файлы (*.mp3 *.wav *.ogg *.flac);;Все файлы (*)"
        )
        if not path:
            return
        self.file_path = path
        self.setWindowTitle(f"{os.path.basename(path)} - BarsikTune")
        self.lbl_track.setText(os.path.basename(path))
        self.player.setSource(QUrl.fromLocalFile(path))
        self.player.play()

        # Inform parent to update recent
        parent = self.parent()
        if parent and hasattr(parent, "_launch_player"):
            # Add to recent without opening new window
            if path in parent.recent_files:
                parent.recent_files.remove(path)
            parent.recent_files.insert(0, path)
            parent.recent_files = parent.recent_files[:3]
            parent._refresh_recent()

    def closeEvent(self, event):
        self.player.stop()
        super().closeEvent(event)
