from wizard.page1 import Page1
from wizard.page2 import Page2
from wizard.page3 import Page3
from dialogs.log import LogDialog

from PySide2.QtWidgets import QWizard, QMessageBox, QStatusBar
import modules, html

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
        self.__status.setToolTip(msg)
        if self.__log is not None:
            return self.__log.append(html.escape(msg) if escape else msg)

    def __page_changed(self):
        if self.currentPage() is not None:
            self.currentPage().children()[0].addWidget(self.__status)
            self.currentPage().update()
            self.currentPage().status.connect(lambda s: self.__status.showMessage(self.__add_log(s, True)))

    def buildUI(self):
        self.__status = QStatusBar(self)

        self.__log = LogDialog(self)

        self.setWizardStyle(QWizard.ClassicStyle)
        self.setButtonLayout([QWizard.Stretch, QWizard.CustomButton1, QWizard.NextButton, QWizard.CancelButton])
        self.setButtonText(QWizard.CustomButton1, "&Logs")
        self.setOption(QWizard.HaveCustomButton1, True)
        self.customButtonClicked.connect(self.__log.show)

        self.currentIdChanged.connect(self.__page_changed)

        page1 = Page1()
        page1.log.connect(lambda msg: self.__add_log(msg, False))
        self.addPage(page1)
        page2 = Page2()
        page2.log.connect(lambda msg: self.__add_log(msg, False))
        self.addPage(page2)
        page3 = Page3()
        page3.log.connect(lambda msg: self.__add_log(msg, False))
        self.addPage(page3)

        # Show window
        self.setWindowTitle('muSync')
        self.show()
        self.resize(self.sizeHint())
