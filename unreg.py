import sys
import winreg
import ctypes
import os
from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QCheckBox, QComboBox, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt

REG_KEY = r"Software\BarsikTune"
REG_VALUE = "FormatsRegistered"

FORMATS = ["mp3", "wav", "ogg", "flac"]

APP_PATH = os.path.abspath(sys.argv[0])


def _is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def _elevate_and_unregister(formats: list[str]):
    fmt_args = " ".join(formats)
    if APP_PATH.endswith(".py"):
        exe = sys.executable
        params = f'"{APP_PATH}" --unregister-system {fmt_args}'
    else:
        exe = APP_PATH
        params = f'--unregister-system {fmt_args}'
    ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)


def _delete_key_tree(hive, path: str):
    """Recursively delete a registry key and all subkeys."""
    try:
        with winreg.OpenKey(hive, path, 0, winreg.KEY_ALL_ACCESS) as key:
            while True:
                try:
                    subkey = winreg.EnumKey(key, 0)
                    _delete_key_tree(hive, rf"{path}\{subkey}")
                except OSError:
                    break
        winreg.DeleteKey(hive, path)
    except OSError:
        pass


def unregister_formats(formats: list[str], for_all_users: bool):
    hive = winreg.HKEY_LOCAL_MACHINE if for_all_users else winreg.HKEY_CURRENT_USER

    for fmt in formats:
        ext = f".{fmt}"
        prog_id = f"BarsikTune.{fmt}"

        # Remove ProgID
        _delete_key_tree(hive, rf"Software\Classes\{prog_id}")

        # Remove OpenWithProgids entry
        try:
            with winreg.OpenKey(hive, rf"Software\Classes\{ext}\OpenWithProgids",
                                0, winreg.KEY_ALL_ACCESS) as k:
                try:
                    winreg.DeleteValue(k, prog_id)
                except OSError:
                    pass
        except OSError:
            pass

        # Remove extension association only if it points to us
        try:
            with winreg.OpenKey(hive, rf"Software\Classes\{ext}",
                                0, winreg.KEY_READ) as k:
                val, _ = winreg.QueryValueEx(k, "")
                if val == prog_id:
                    _delete_key_tree(hive, rf"Software\Classes\{ext}")
        except OSError:
            pass

    # Remove registration flag
    try:
        with winreg.OpenKey(hive, REG_KEY, 0, winreg.KEY_ALL_ACCESS) as k:
            try:
                winreg.DeleteValue(k, REG_VALUE)
            except OSError:
                pass
        winreg.DeleteKey(hive, REG_KEY)
    except OSError:
        pass

    ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)


def _get_registered_formats(hive) -> list[str]:
    """Return which formats are currently registered in the given hive."""
    found = []
    for fmt in FORMATS:
        try:
            with winreg.OpenKey(hive, rf"Software\Classes\BarsikTune.{fmt}"):
                found.append(fmt)
        except OSError:
            pass
    return found


def _handle_system_unregistration():
    formats = sys.argv[2:]
    if not formats:
        sys.exit(1)
    try:
        unregister_formats(formats, for_all_users=True)
        sys.exit(0)
    except Exception as e:
        ctypes.windll.user32.MessageBoxW(0, str(e), "Ошибка разрегистрации", 0x10)
        sys.exit(1)


class UnregistrationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Разрегистрация форматов")
        self.setFixedSize(340, 230)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowTitleHint
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        lbl = QLabel("Разрегистрировать форматы:")
        layout.addWidget(lbl)

        # Detect what's registered where
        reg_user = _get_registered_formats(winreg.HKEY_CURRENT_USER)
        reg_system = _get_registered_formats(winreg.HKEY_LOCAL_MACHINE)
        reg_any = set(reg_user) | set(reg_system)

        self.checkboxes: dict[str, QCheckBox] = {}
        row1 = QHBoxLayout()
        row2 = QHBoxLayout()
        for i, fmt in enumerate(FORMATS):
            cb = QCheckBox(fmt.upper())
            cb.setChecked(fmt in reg_any)
            cb.setEnabled(fmt in reg_any)
            self.checkboxes[fmt] = cb
            (row1 if i < 2 else row2).addWidget(cb)
        row1.addStretch()
        row2.addStretch()
        layout.addLayout(row1)
        layout.addLayout(row2)

        if not reg_any:
            notice = QLabel("Нет зарегистрированных форматов.")
            notice.setStyleSheet("color: gray;")
            layout.addWidget(notice)

        scope_lbl = QLabel("Разрегистрировать для:")
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

        self.btn_unreg = QPushButton("Разрегистрировать!")
        self.btn_unreg.setEnabled(bool(reg_any))
        self.btn_unreg.clicked.connect(self._do_unregister)

        btn_row.addWidget(btn_cancel)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_unreg)
        layout.addLayout(btn_row)

    def _do_unregister(self):
        selected = [fmt for fmt, cb in self.checkboxes.items() if cb.isChecked()]
        if not selected:
            QMessageBox.warning(self, "BarsikTune", "Выберите хотя бы один формат.")
            return

        for_all = self.scope_combo.currentIndex() == 1

        if for_all and not _is_admin():
            QMessageBox.information(
                self, "BarsikTune",
                "Для разрегистрации для всех пользователей потребуются права администратора.\n"
                "Windows запросит подтверждение."
            )
            _elevate_and_unregister(selected)
            self.accept()
            return

        try:
            unregister_formats(selected, for_all_users=for_all)
            QMessageBox.information(
                self, "BarsikTune",
                f"Форматы успешно разрегистрированы:\n{', '.join(f.upper() for f in selected)}"
            )
            self.accept()
        except PermissionError:
            QMessageBox.critical(
                self, "Ошибка",
                "Недостаточно прав для изменения реестра.\n"
                "Попробуйте запустить от имени администратора."
            )
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "--unregister-system":
        _handle_system_unregistration()

    app = QApplication(sys.argv)
    dlg = UnregistrationDialog()
    dlg.exec()
    sys.exit(0)


if __name__ == "__main__":
    main()
