from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTextBrowser, QCheckBox, QPushButton
from PyQt5.QtGui import QIcon

class LogDialog(QDialog):
    def __copy_log(self):
        self.findChild(QTextBrowser, "log").selectAll()
        self.findChild(QTextBrowser, "log").copy()

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("muSync - Logs")
        self.resize(540, 250)
        self.setModal(False)
        logLayout = QVBoxLayout(self)
        logBrowser = QTextBrowser()
        logBrowser.setObjectName("log")
        logBrowser.setAcceptRichText(True)
        logBrowser.setReadOnly(True)
        logLayout.addWidget(logBrowser)
        buttonsLayout = QHBoxLayout()
        autoScroll = QCheckBox("Auto-scroll")
        autoScroll.setObjectName("autoscroll")
        autoScroll.setChecked(True)
        buttonsLayout.addWidget(autoScroll)
        clearButton = QPushButton(QIcon.fromTheme("delete"), "C&lear")
        clearButton.clicked.connect(logBrowser.clear)
        buttonsLayout.addWidget(clearButton)
        copyButton = QPushButton(QIcon.fromTheme("edit-copy"), "Co&py")
        copyButton.clicked.connect(self.__copy_log)
        buttonsLayout.addWidget(copyButton)
        closeButton = QPushButton(QIcon.fromTheme("dialog-close"), "&Close")
        closeButton.clicked.connect(self.close)
        buttonsLayout.addWidget(closeButton)
        logLayout.addLayout(buttonsLayout)
