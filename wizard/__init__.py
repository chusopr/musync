from PySide2.QtWidgets import QWizardPage
from PySide2.QtCore import Signal
from abc import abstractmethod

class WizardPage(QWizardPage):
    __completed = False
    status = Signal(str)
    log = Signal(str)

    @abstractmethod
    def update(self):
        pass

    def setCompleted(self, c):
        self.__completed = c
        self.completeChanged.emit()

    def isComplete(self):
        return self.__completed
