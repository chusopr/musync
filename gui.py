from wizard.page1 import Page1
from dialogs.log import LogDialog

from PyQt5.QtWidgets import QWizard, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QLabel, QComboBox, QDialog, QMessageBox, QListWidgetItem, QStatusBar, QTextBrowser, QCheckBox, QScrollArea
from PyQt5.QtGui import QIcon, QColor
from datetime import datetime
import re, modules, threading, cgi, json, os
from sys import stderr

class MainWindow(QWizard):
    __log = None
    __status = None

    def __init__(self):
        super().__init__()
        self.buildUI()
        modules.load()

    def __bogus_module(self, module_name):
        errorMsg = QMessageBox(QMessageBox.Critical, "Bogus module", module_name + " module is not working properly", QMessageBox.Ok, self)
        errorMsg.show()

    def __add_log(self, msg, escape=True):
        if self.__log is not None:
            self.__log.append('<span style="color: #bebebe">{} - </span>{}'.format(datetime.now(), cgi.escape(msg) if escape else msg))

    def __page_changed(self):
        if self.currentPage() is not None:
            self.currentPage().children()[0].addWidget(self.__status)
            self.currentPage().update()
            self.currentPage().status.connect(self.__status.showMessage)

    def buildUI(self):
        Page1(self).log.connect(lambda msg: self.__add_log(msg, False))

        self.__status = QStatusBar(self)
        self.__status.messageChanged.connect(self.__add_log)

        self.__log = LogDialog(self)

        self.setButtonText(QWizard.CustomButton1, "&Logs")
        self.setOption(QWizard.HaveCustomButton1, True)
        self.customButtonClicked.connect(self.__log.show)

        self.currentIdChanged.connect(self.__page_changed)

        # Show window
        self.setWindowTitle('muSync')
        self.show()
