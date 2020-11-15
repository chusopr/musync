from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTextBrowser, QCheckBox, QPushButton
from PyQt5.QtGui import QIcon
from datetime import datetime

class LogDialog(QDialog):
    __log = None
    __autoScroll = None

    def __copy_log(self):
        self.__log.selectAll()
        self.__log.copy()

    def __scroll(self):
        if self.__autoScroll.isChecked():
            self.__log.verticalScrollBar().setValue(self.__log.verticalScrollBar().maximum())

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("muSync - Logs")
        self.resize(540, 250)
        self.setModal(False)
        logLayout = QVBoxLayout(self)
        self.__log = QTextBrowser(parent)
        self.__log.setAcceptRichText(True)
        self.__log.setReadOnly(True)
        self.__log.textChanged.connect(self.__scroll)
        logLayout.addWidget(self.__log)
        buttonsLayout = QHBoxLayout()
        self.__autoScroll = QCheckBox("Auto-scroll")
        self.__autoScroll.setChecked(True)
        buttonsLayout.addWidget(self.__autoScroll)
        clearButton = QPushButton(QIcon.fromTheme("edit-delete"), "C&lear")
        clearButton.clicked.connect(self.__log.clear)
        buttonsLayout.addWidget(clearButton)
        copyButton = QPushButton(QIcon.fromTheme("edit-copy"), "Co&py")
        copyButton.clicked.connect(self.__copy_log)
        buttonsLayout.addWidget(copyButton)
        closeButton = QPushButton(QIcon.fromTheme("dialog-close"), "&Close")
        closeButton.clicked.connect(self.close)
        buttonsLayout.addWidget(closeButton)
        logLayout.addLayout(buttonsLayout)

    def append(self, s):
        datestr = str(datetime.now())
        self.__log.append('<span style="color: #bebebe">{} - </span>{}'.format(datestr, s))
        return self.__log.document().lastBlock().text()[len(datestr)+3:]
