import sys
import os
import json
from PyQt5.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QWidget,
    QProgressBar, QTabWidget, QAction, QInputDialog, QTabBar, QToolButton,
    QGraphicsDropShadowEffect, QLabel, QCompleter, QMenu
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, Qt, QObject, QEvent, QTimer
from PyQt5.QtGui import QColor, QFont, QIcon
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest

# ------------------ Close Button ------------------
class OutlineButton(QToolButton):
    def __init__(self, browser, tab_widget, get_index_func):
        super().__init__()
        self.browser = browser
        self.tab_widget = tab_widget
        self.get_index_func = get_index_func
        self.setText("✕")
        self.setFont(QFont("", 10, QFont.Bold))
        self.setStyleSheet("color: white; background: transparent;")
        effect = QGraphicsDropShadowEffect()
        effect.setColor(QColor("black"))
        effect.setOffset(0, 0)
        effect.setBlurRadius(3)
        self.setGraphicsEffect(effect)
        self.clicked.connect(self.close_tab)

    def close_tab(self):
        index = self.get_index_func()
        if index != -1:
            self.browser.close_tab(index)

# ------------------ Plus Button ------------------
class PlusButton(QToolButton):
    def __init__(self, tab_widget, add_tab_func):
        super().__init__(tab_widget)
        self.tab_widget = tab_widget
        self.add_tab_func = add_tab_func
        self.setStyleSheet("""
            background-color: white;
            border: none;
            border-radius: 2px;
        """)
        self.setFixedSize(28, 28)

        self.label = QLabel("+", self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setFont(QFont("", 16, QFont.Bold))
        shadow = QGraphicsDropShadowEffect()
        shadow.setColor(QColor("black"))
        shadow.setOffset(0, 0)
        shadow.setBlurRadius(3)
        self.label.setGraphicsEffect(shadow)
        self.label.setStyleSheet("color: white; background: transparent;")
        self.clicked.connect(self.add_tab_func)
        self.show()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.label.setGeometry(0, 0, self.width(), self.height())

# ------------------ TabBar Watcher ------------------
class TabBarWatcher(QObject):
    def __init__(self, tab_widget, plus_button):
        super().__init__()
        self.tab_widget = tab_widget
        self.plus_button = plus_button
        self.tab_bar = tab_widget.tabBar()
        self.tab_bar.installEventFilter(self)
        self.timer = QTimer()
        self.timer.setInterval(10)
        self.timer.timeout.connect(self.update_plus_button_position)
        self.timer.start()

    def eventFilter(self, obj, event):
        if obj == self.tab_bar and event.type() in (QEvent.Resize, QEvent.Show, QEvent.Move):
            self.update_plus_button_position()
        return super().eventFilter(obj, event)

    def update_plus_button_position(self):
        count = self.tab_bar.count()
        x = 4 if count == 0 else self.tab_bar.tabRect(count - 1).right() + 5
        y = (self.tab_bar.height() - self.plus_button.height()) // 2
        self.plus_button.move(x, y)
        self.plus_button.raise_()

# ------------------ Browser ------------------
class Browser(QMainWindow):
    def __init__(self):
        super().__init__()

        # --- Icon fix: set absolute path for icon ---
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(base_path, "assets", "icon.ico")
        self.setWindowIcon(QIcon(icon_path))

        # Window setup
        self.setWindowTitle("Cobalt Browser")
        self.setGeometry(100, 100, 1000, 700)
        self.setWindowFlags(Qt.Window)  # Ensure taskbar shows icon

        self.network_manager = QNetworkAccessManager()
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(False)
        self.tabs.setMovable(True)
        self.tabs.tabBar().setExpanding(False)
        self.setCentralWidget(self.tabs)

        self.bookmarks = []
        self.history = []

        # Menu
        self.menu = self.menuBar()
        self.bookmarks_menu = self.menu.addMenu("Bookmarks")
        add_bookmark_action = QAction("Add Bookmark", self)
        add_bookmark_action.triggered.connect(self.add_bookmark)
        self.bookmarks_menu.addAction(add_bookmark_action)
        self.bookmarks_menu.addSeparator()

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.statusBar().addPermanentWidget(self.progress)

        # Plus button
        self.plus_button = PlusButton(self.tabs, lambda: self.add_tab("https://google.com", "New Tab"))
        self.plus_button.setParent(self.tabs)
        self.plus_button.show()

        # Watcher
        self.watcher = TabBarWatcher(self.tabs, self.plus_button)
        self.tabs.tabBar().tabMoved.connect(lambda *args: self.watcher.update_plus_button_position())

        # Initial tab
        self.add_tab("https://google.com", "Home")

    # ------------------ Add Tab ------------------
    def add_tab(self, url=None, label="New Tab"):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Navigation bar
        nav_layout = QHBoxLayout()
        back_btn = QPushButton("←")
        forward_btn = QPushButton("→")
        reload_btn = QPushButton("⟳")
        url_bar = QLineEdit()
        url_bar.setPlaceholderText("Search or enter web address")
        url_bar.setStyleSheet("QLineEdit { border-radius: 12px; padding: 4px; border: 1px solid gray; }")

        url_bar._user_typing = False
        url_bar.installEventFilter(self)

        completer = QCompleter([], url_bar)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        url_bar.setCompleter(completer)

        def on_text_edited(text):
            url_bar._user_typing = True
            self.fetch_online_suggestions(text, completer)

        url_bar.textEdited.connect(on_text_edited)

        nav_layout.addWidget(back_btn)
        nav_layout.addWidget(forward_btn)
        nav_layout.addWidget(reload_btn)
        nav_layout.addWidget(url_bar)
        layout.addLayout(nav_layout)

        # Web view
        web_view = QWebEngineView()
        layout.addWidget(web_view)

        # Smooth scrolling injection
        web_view.loadFinished.connect(lambda _: self.enable_smooth_scroll(web_view))

        url_bar.returnPressed.connect(lambda: self.load_url(web_view, url_bar))
        web_view.urlChanged.connect(lambda qurl: url_bar.setText(qurl.toString()))
        back_btn.clicked.connect(web_view.back)
        forward_btn.clicked.connect(web_view.forward)
        reload_btn.clicked.connect(web_view.reload)

        if url and not url.startswith("http"):
            url = "http://" + url
        if url:
            web_view.load(QUrl(url))

        # Custom context menu
        web_view.setContextMenuPolicy(Qt.CustomContextMenu)
        web_view.customContextMenuRequested.connect(
            lambda pos, wv=web_view: self.show_custom_context_menu(pos, wv)
        )

        # Tab setup
        index = self.tabs.count()
        self.tabs.addTab(tab, "")
        self.set_tab_label(tab, label)
        self.tabs.setCurrentWidget(tab)

        btn = OutlineButton(self, self.tabs, lambda tab=tab: self.tabs.indexOf(tab))
        btn.setFixedSize(16, 16)
        self.tabs.tabBar().setTabButton(index, QTabBar.RightSide, btn)
        self.watcher.update_plus_button_position()

    # ------------------ Smooth scroll ------------------
    def enable_smooth_scroll(self, web_view):
        js = """
        // Enable smooth scrolling for wheel, touchpad, and arrow keys
        document.documentElement.style.scrollBehavior = 'smooth';

        document.addEventListener('wheel', function(e) {
            e.preventDefault();
            window.scrollBy({top: e.deltaY, left: e.deltaX, behavior: 'smooth'});
        }, {passive: false});

        document.addEventListener('keydown', function(e) {
            let amount = 40;
            if (e.key === 'ArrowDown') { window.scrollBy({top: amount, behavior:'smooth'}); e.preventDefault(); }
            if (e.key === 'ArrowUp')   { window.scrollBy({top: -amount, behavior:'smooth'}); e.preventDefault(); }
            if (e.key === 'PageDown')  { window.scrollBy({top: window.innerHeight, behavior:'smooth'}); e.preventDefault(); }
            if (e.key === 'PageUp')    { window.scrollBy({top: -window.innerHeight, behavior:'smooth'}); e.preventDefault(); }
        });
        """
        web_view.page().runJavaScript(js)

    # ------------------ Custom context menu ------------------
    def show_custom_context_menu(self, pos, web_view):
        page = web_view.page()
        menu = page.createStandardContextMenu()  # preserve standard options

        # Detect if a video element is under cursor
        js_check_video = """
        (function() {
            var el = document.elementFromPoint(%d, %d);
            while(el) {
                if (el.tagName && el.tagName.toLowerCase() === 'video') return true;
                el = el.parentElement;
            }
            return false;
        })()
        """ % (pos.x(), pos.y())

        def add_pip_if_video(result):
            if result:  # Only add PiP if cursor is on a video
                pip_action = QAction("Picture in Picture", web_view)
                pip_action.triggered.connect(lambda: self.activate_pip(web_view))
                menu.insertAction(menu.actions()[0] if menu.actions() else None, pip_action)
                menu.insertSeparator(menu.actions()[1] if len(menu.actions()) > 1 else None)
            menu.exec_(web_view.mapToGlobal(pos))

        page.runJavaScript(js_check_video, add_pip_if_video)

    # ------------------ Activate PiP ------------------
    def activate_pip(self, web_view):
        js = """
        var video = document.querySelector('video');
        if (video) {
            if (document.pictureInPictureElement) {
                document.exitPictureInPicture();
            } else {
                video.requestPictureInPicture();
            }
        }
        """
        web_view.page().runJavaScript(js)

    # ------------------ Event filter for URL bar ------------------
    def eventFilter(self, obj, event):
        if isinstance(obj, QLineEdit):
            if event.type() in (QEvent.MouseButtonPress, QEvent.FocusIn):
                if not getattr(obj, "_user_typing", False):
                    if obj.cursorPosition() == 0 or obj.selectedText() != obj.text():
                        QTimer.singleShot(0, obj.selectAll)
        return super().eventFilter(obj, event)

    # ------------------ Autocomplete ------------------
    def fetch_online_suggestions(self, text, completer):
        if not text.strip():
            return
        url = f"https://suggestqueries.google.com/complete/search?client=firefox&q={text}"
        request = QNetworkRequest(QUrl(url))
        reply = self.network_manager.get(request)
        reply.finished.connect(lambda r=reply, c=completer: self.handle_suggestions(r, c))

    def handle_suggestions(self, reply, completer):
        data = reply.readAll()
        try:
            suggestions = json.loads(str(data, 'utf-8'))[1]
            completer.model().setStringList(suggestions)
        except Exception as e:
            print("Error parsing suggestions:", e)

    # ------------------ Tab label helpers ------------------
    def update_tab_label(self, tab, title):
        index = self.tabs.indexOf(tab)
        if index != -1:
            self.tabs.tabBar().setTabText(index, title)

    def set_tab_label(self, tab, label):
        self.update_tab_label(tab, label)

    # ------------------ Load URL ------------------
    def load_url(self, web_view, url_bar):
        query = url_bar.text().strip()
        if not query:
            return
        if "." not in query:
            url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        else:
            url = query if query.startswith("http") else "http://" + query
        web_view.load(QUrl(url))
        if url not in self.history:
            self.history.append(url)

    # ------------------ Close tab ------------------
    def close_tab(self, index):
        if index != -1 and self.tabs.count() > 1:
            self.tabs.removeTab(index)
            self.watcher.update_plus_button_position()
        else:
            self.close()

    # ------------------ Bookmarks ------------------
    def add_bookmark(self):
        current_tab = self.tabs.currentWidget()
        web_view = current_tab.findChild(QWebEngineView)
        url = web_view.url().toString()
        text, ok = QInputDialog.getText(self, "Bookmark Name", "Enter bookmark name:")
        if ok and text:
            self.bookmarks.append((text, url))
            action = QAction(text, self)
            action.triggered.connect(lambda _, u=url: self.add_tab(u, text))
            self.bookmarks_menu.addAction(action)
