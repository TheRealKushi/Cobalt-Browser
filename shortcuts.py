from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import Qt, QObject, QEvent

class Shortcuts(QObject):
    def __init__(self, browser):
        super().__init__(browser)
        self.browser = browser
        self.closed_tabs_stack = []  # For reopening closed tabs
        self.browser.installEventFilter(self)  # Capture all key presses

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            ctrl = event.modifiers() & Qt.ControlModifier
            shift = event.modifiers() & Qt.ShiftModifier
            key = event.key()

            # Ctrl+Z → Back
            if ctrl and not shift and key == Qt.Key_Z:
                self.go_back()
                return True
            # Ctrl+Y → Forward
            elif ctrl and not shift and key == Qt.Key_Y:
                self.go_forward()
                return True
            # Ctrl+R → Reload
            elif ctrl and not shift and key == Qt.Key_R:
                self.refresh_tab()
                return True
            # Ctrl+T → New tab
            elif ctrl and not shift and key == Qt.Key_T:
                self.new_tab()
                return True
            # Ctrl+W → Close tab
            elif ctrl and not shift and key == Qt.Key_W:
                self.close_tab()
                return True
            # Ctrl+Shift+T → Reopen last closed tab
            elif ctrl and shift and key == Qt.Key_T:
                self.reopen_last_closed_tab()
                return True
            # Ctrl+Shift+K → Duplicate tab
            elif ctrl and shift and key == Qt.Key_K:
                self.duplicate_tab()
                return True
            # Ctrl+M → Mute
            elif ctrl and not shift and key == Qt.Key_M:
                self.mute_tab()
                return True

        return super().eventFilter(obj, event)

    # ---------- Shortcut functions ----------
    def current_webview(self):
        tab = self.browser.tabs.currentWidget()
        if tab:
            return tab.findChild(QWebEngineView)
        return None

    def go_back(self):
        webview = self.current_webview()
        if webview:
            webview.back()

    def go_forward(self):
        webview = self.current_webview()
        if webview:
            webview.forward()

    def refresh_tab(self):
        webview = self.current_webview()
        if webview:
            webview.reload()

    def new_tab(self):
        self.browser.add_tab("https://google.com", "New Tab")

    def close_tab(self):
        index = self.browser.tabs.currentIndex()
        if index != -1:
            tab = self.browser.tabs.widget(index)
            webview = tab.findChild(QWebEngineView)
            if webview:
                self.closed_tabs_stack.append((webview.url().toString(), self.browser.tabs.tabText(index)))
            self.browser.close_tab(index)

    def reopen_last_closed_tab(self):
        if self.closed_tabs_stack:
            url, label = self.closed_tabs_stack.pop()
            self.browser.add_tab(url, label)

    def duplicate_tab(self):
        tab = self.browser.tabs.currentWidget()
        if tab:
            webview = tab.findChild(QWebEngineView)
            if webview:
                url = webview.url().toString()
                label = self.browser.tabs.tabText(self.browser.tabs.currentIndex())
                self.browser.add_tab(url, label)

    def mute_tab(self):
        webview = self.current_webview()
        if webview:
            is_muted = webview.page().isAudioMuted()
            webview.page().setAudioMuted(not is_muted)
