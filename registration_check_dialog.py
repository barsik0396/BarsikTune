from enum import IntEnum
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt


class RegistrationCheckDialog(QDialog):
    class Result(IntEnum):
        CANCEL = 0
        REGISTER = 2
        OPEN_WITHOUT = 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("BarsikTune")
        self.setFixedSize(280, 150)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowTitleHint
        )
        self._result = self.Result.CANCEL

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        lbl = QLabel("Выберите действие:")
        layout.addWidget(lbl)

        btn_register = QPushButton("Зарегистрировать форматы")
        btn_register.clicked.connect(self._on_register)
        layout.addWidget(btn_register)

        btn_open = QPushButton("Открыть без регистрации")
        btn_open.clicked.connect(self._on_open_without)
        layout.addWidget(btn_open)

        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self._on_cancel)
        layout.addWidget(btn_cancel)

    def _on_register(self):
        self._result = self.Result.REGISTER
        self.accept()

    def _on_open_without(self):
        self._result = self.Result.OPEN_WITHOUT
        self.accept()

    def _on_cancel(self):
        self._result = self.Result.CANCEL
        self.reject()

    def exec(self) -> "RegistrationCheckDialog.Result":
        super().exec()
        return self._result
