import sys
import os
from PyQt5.QtWidgets import QApplication, QAction
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QTimer
from ui import Browser
from shortcuts import Shortcuts
from updater import Updater  # ← new import

# --- App metadata ---
APP_VERSION = "1.0.1"  # bump this each release
UPDATE_FEED = "https://therealkushi.github.io/Cobalt-Browser/updates.json"
APP_ID = "cobalt.browser.1.0.1"  # Windows taskbar AppUserModelID

if __name__ == "__main__":
    # Get absolute path to icon (works for PyInstaller too)
    if getattr(sys, 'frozen', False):
        # If running as a bundled exe
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(base_path, "assets", "icon.ico")

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(icon_path))

    browser = Browser()
    browser.setWindowIcon(QIcon(icon_path))

    # Make sure window is recognized for taskbar
    browser.setWindowFlags(Qt.Window)

    # On Windows, force the app to use the icon in the taskbar
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)

    # --- Updater setup ---
    updater = Updater(browser, APP_VERSION, UPDATE_FEED, app_name="Cobalt Browser")

    # Add Help > Check for Updates...
    help_menu = browser.menu.addMenu("Help")
    check_action = QAction("Check for Updates…", browser)
    check_action.triggered.connect(lambda: updater.check(silent=False))
    help_menu.addAction(check_action)

    # Auto-check a few seconds after startup
    QTimer.singleShot(3000, lambda: updater.check(silent=True))

    Shortcuts(browser)
    browser.show()
    sys.exit(app.exec_())
