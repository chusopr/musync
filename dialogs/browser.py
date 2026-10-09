from PySide6.QtCore import QEventLoop, QUrl, QTimer, Slot
from PySide6.QtWidgets import QDialog, QVBoxLayout
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtNetwork import QNetworkCookie

class Browser(QDialog):

    def __init__(self, parent):
        # We don't set the parent immediately
        # because that will make the window tiny
        super().__init__()
        self.setModal(True)
        # Instead, we add all the widgets first
        # and let Qt calculate the window size
        layout = QVBoxLayout(self)
        self.__webview = QWebEngineView()
        # Setup cookie tracking
        self.__cookies = {}
        cookie_store = self.__webview.page().profile().cookieStore()
        cookie_store.cookieAdded.connect(self.__cookie_added)
        cookie_store.cookieRemoved.connect(self.__cookie_removed)
        cookie_store.loadAllCookies()
        layout.addWidget(self.__webview)
        self.setLayout(layout)
        # We save the current size that was calculated by Qt
        size = self.size()
        # We need to save the window flags because setParent()
        # will clear them making the window invisible
        flags = self.windowFlags()
        # Now we can set the parent
        self.setParent(parent)
        # Restore size and window flags
        self.resize(size)
        self.setWindowFlags(flags)

    def wait(self, condition, interval=500):
        result = None
        timer = QTimer(self)
        loop = QEventLoop()

        def check():
            nonlocal result, timer
            result = condition(self)
            if result:
                timer.stop()
                loop.quit()
                del timer

        timer.timeout.connect(check)
        self.finished.connect(timer.deleteLater)
        timer.destroyed.connect(loop.quit)

        timer.start(interval)
        loop.exec()
        return result

    def run_js(self, js):
        loop = QEventLoop()
        result = None

        def callback(r):
            nonlocal result, loop
            result = r
            loop.quit()

        self.__webview.page().runJavaScript(js, 0, lambda r: callback(r))
        loop.exec()
        return result

    @Slot(QNetworkCookie)
    def __cookie_added(self, cookie):
        self.__cookies[cookie.name()] = cookie

    @Slot(QNetworkCookie)
    def __cookie_removed(self, cookie):
        if cookie.name() in self.__cookies:
            del self.__cookies[cookie.name()]

    def get(self, url):
        loop = QEventLoop()
        self.__webview.page().loadFinished.connect(loop.quit)
        self.__webview.setUrl(QUrl(url))
        loop.exec()

    def get_url(self):
        return self.__webview.page().url()

    def get_cookies(self):
        return self.__cookies.values()
