import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QFileDialog, QListWidget,
    QListWidgetItem
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from player_window import PlayerWindow

RECENT_MAX = 3


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BarsikTune")
        self.setMinimumWidth(420)
        self.setFixedHeight(320)

        self.recent_files: list[str] = []
        self.selected_file: str | None = None
        self.player_window: PlayerWindow | None = None

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        # --- Недавнее ---
        recent_label = QLabel("Недавнее:")
        recent_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bold = QFont()
        bold.setBold(True)
        recent_label.setFont(bold)
        layout.addWidget(recent_label)

        self.recent_list = QListWidget()
        self.recent_list.setFixedHeight(90)
        self.recent_list.itemDoubleClicked.connect(self._open_recent)
        layout.addWidget(self.recent_list)

        self._refresh_recent()

        # --- Начать ---
        start_label = QLabel("Начать:")
        start_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        start_label.setFont(bold)
        layout.addWidget(start_label)

        choose_row = QHBoxLayout()
        choose_row.setSpacing(8)
        btn_choose = QPushButton("Выбрать...")
        btn_choose.setFixedWidth(100)
        btn_choose.clicked.connect(self._choose_file)
        self.lbl_file = QLabel("Файл не выбран")
        self.lbl_file.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        choose_row.addWidget(btn_choose)
        choose_row.addWidget(self.lbl_file, 1)
        layout.addLayout(choose_row)

        btn_open = QPushButton("Открыть!")
        btn_open.setFixedWidth(120)
        btn_open.clicked.connect(self._open_file)
        open_row = QHBoxLayout()
        open_row.addStretch()
        open_row.addWidget(btn_open)
        open_row.addStretch()
        layout.addLayout(open_row)

        layout.addStretch()

    def _refresh_recent(self):
        self.recent_list.clear()
        if not self.recent_files:
            self.recent_list.addItem("Пусто :(")
            return
        for path in self.recent_files:
            self.recent_list.addItem(os.path.basename(path))
        while self.recent_list.count() < RECENT_MAX:
            self.recent_list.addItem("Пусто :(")

    def _choose_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Выбрать MP3", "", "Аудио файлы (*.mp3 *.wav *.ogg *.flac);;Все файлы (*)"
        )
        if path:
            self.selected_file = path
            self.lbl_file.setText(os.path.basename(path))

    def _open_file(self):
        if not self.selected_file:
            return
        self._launch_player(self.selected_file)

    def _open_recent(self, item: QListWidgetItem):
        text = item.text()
        if text == "Пусто :(":
            return
        for path in self.recent_files:
            if os.path.basename(path) == text:
                self._launch_player(path)
                return

    def _launch_player(self, path: str):
        if path in self.recent_files:
            self.recent_files.remove(path)
        self.recent_files.insert(0, path)
        self.recent_files = self.recent_files[:RECENT_MAX]
        self._refresh_recent()

        if self.player_window and self.player_window.isVisible():
            self.player_window.close()

        self.player_window = PlayerWindow(path, self)
        self.player_window.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
