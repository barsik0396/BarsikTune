import sys
import winreg
from PySide6.QtWidgets import QApplication

FORMATS = ["mp3", "wav", "ogg", "flac"]
REG_KEY = r"Software\BarsikTune"
REG_VALUE = "FormatsRegistered"


def is_registered() -> bool:
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            # HKLM requires KEY_READ which is allowed without admin for reading
            access = winreg.KEY_READ
            if hive == winreg.HKEY_LOCAL_MACHINE:
                access |= winreg.KEY_WOW64_64KEY
            with winreg.OpenKey(hive, REG_KEY, 0, access) as key:
                val, _ = winreg.QueryValueEx(key, REG_VALUE)
                if val == 1:
                    return True
        except OSError:
            pass
    return False


def _handle_system_registration():
    """Called when re-launched with UAC elevation to register for all users."""
    formats = sys.argv[2:]  # --register-system fmt1 fmt2 ...
    if not formats:
        sys.exit(1)
    from registration_dialog import register_formats
    try:
        register_formats(formats, for_all_users=True)
        sys.exit(0)
    except Exception as e:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, str(e), "Ошибка регистрации", 0x10)
        sys.exit(1)


def main():
    # Elevated re-launch for system-wide registration — no GUI needed
    if len(sys.argv) >= 2 and sys.argv[1] == "--register-system":
        _handle_system_registration()

    app = QApplication(sys.argv)

    if not is_registered():
        from registration_check_dialog import RegistrationCheckDialog
        dlg = RegistrationCheckDialog()
        result = dlg.exec()

        if result == RegistrationCheckDialog.Result.CANCEL:
            sys.exit(0)
        elif result == RegistrationCheckDialog.Result.REGISTER:
            from registration_dialog import RegistrationDialog
            reg_dlg = RegistrationDialog()
            if not reg_dlg.exec():
                sys.exit(0)
        # OPEN_WITHOUT — просто продолжаем

    from main_window import MainWindow
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
