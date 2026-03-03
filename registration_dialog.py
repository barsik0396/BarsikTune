import sys
import winreg
import ctypes
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QCheckBox, QComboBox, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt

REG_KEY = r"Software\BarsikTune"
REG_VALUE = "FormatsRegistered"

FORMATS = ["mp3", "wav", "ogg", "flac"]

APP_PATH = os.path.abspath(sys.argv[0])
if APP_PATH.endswith(".py"):
    OPEN_CMD = f'"{sys.executable}" "{APP_PATH}" "%1"'
else:
    OPEN_CMD = f'"{APP_PATH}" "%1"'


def _is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def _elevate_and_register(formats: list[str]):
    """Re-launch with UAC elevation to write into HKLM."""
    fmt_args = " ".join(formats)
    if APP_PATH.endswith(".py"):
        # Running as script: python.exe "main.py" --register-system mp3 wav ...
        exe = sys.executable
        params = f'"{APP_PATH}" --register-system {fmt_args}'
    else:
        # Running as frozen exe
        exe = APP_PATH
        params = f'--register-system {fmt_args}'
    ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)


def register_formats(formats: list[str], for_all_users: bool):
    hive = winreg.HKEY_LOCAL_MACHINE if for_all_users else winreg.HKEY_CURRENT_USER

    for fmt in formats:
        ext = f".{fmt}"
        prog_id = f"BarsikTune.{fmt}"

        with winreg.CreateKey(hive, rf"Software\Classes\{prog_id}") as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, f"Аудио файл {fmt.upper()}")
        with winreg.CreateKey(hive, rf"Software\Classes\{prog_id}\shell\open\command") as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, OPEN_CMD)

        with winreg.CreateKey(hive, rf"Software\Classes\{ext}") as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, prog_id)

        with winreg.CreateKey(hive, rf"Software\Classes\{ext}\OpenWithProgids") as k:
            winreg.SetValueEx(k, prog_id, 0, winreg.REG_NONE, b"")

    # Mark as registered so main.py won't show the dialog again
    with winreg.CreateKey(hive, REG_KEY) as k:
        winreg.SetValueEx(k, REG_VALUE, 0, winreg.REG_DWORD, 1)

    ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)


class RegistrationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Регистрация форматов")
        self.setFixedSize(340, 210)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowTitleHint
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        lbl = QLabel("Зарегистрировать форматы:")
        layout.addWidget(lbl)

        self.checkboxes: dict[str, QCheckBox] = {}
        row1 = QHBoxLayout()
        row2 = QHBoxLayout()
        for i, fmt in enumerate(FORMATS):
            cb = QCheckBox(fmt.upper())
            cb.setChecked(True)
            self.checkboxes[fmt] = cb
            (row1 if i < 2 else row2).addWidget(cb)
        row1.addStretch()
        row2.addStretch()
        layout.addLayout(row1)
        layout.addLayout(row2)

        scope_lbl = QLabel("Регистрировать для:")
        layout.addWidget(scope_lbl)

        self.scope_combo = QComboBox()
        self.scope_combo.addItem("Этого пользователя")
        self.scope_combo.addItem("Всех пользователей")
        layout.addWidget(self.scope_combo)

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Отмена")
        btn_cancel.setFixedWidth(90)
        btn_cancel.clicked.connect(self.reject)

        btn_register = QPushButton("Зарегистрировать!")
        btn_register.clicked.connect(self._do_register)

        btn_row.addWidget(btn_cancel)
        btn_row.addStretch()
        btn_row.addWidget(btn_register)
        layout.addLayout(btn_row)

    def _do_register(self):
        selected = [fmt for fmt, cb in self.checkboxes.items() if cb.isChecked()]
        if not selected:
            QMessageBox.warning(self, "BarsikTune", "Выберите хотя бы один формат.")
            return

        for_all = self.scope_combo.currentIndex() == 1

        if for_all and not _is_admin():
            QMessageBox.information(
                self, "BarsikTune",
                "Для регистрации для всех пользователей потребуются права администратора.\n"
                "Windows запросит подтверждение."
            )
            _elevate_and_register(selected)
            # Elevated process writes the key and exits.
            # Current process just opens the player normally.
            self.accept()
            return

        try:
            register_formats(selected, for_all_users=for_all)
            QMessageBox.information(
                self, "BarsikTune",
                f"Форматы успешно зарегистрированы:\n{', '.join(f.upper() for f in selected)}"
            )
            self.accept()
        except PermissionError:
            QMessageBox.critical(
                self, "Ошибка",
                "Недостаточно прав для записи в реестр.\n"
                "Попробуйте запустить от имени администратора."
            )
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
