from PyQt5.QtWidgets import QWizardPage
from PyQt5.QtCore import pyqtSignal
from abc import abstractmethod

class WizardPage(QWizardPage):
    __completed = False
    status = pyqtSignal(str)
    log = pyqtSignal(str)

    @abstractmethod
    def update(self):
        pass

    def setCompleted(self, c):
        self.__completed = c
        self.completeChanged.emit()

    def isComplete(self):
        return self.__completed
