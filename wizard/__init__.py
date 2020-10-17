from PyQt5.QtWidgets import QWizard, QWizardPage
from abc import abstractmethod

class WizardPage(QWizardPage):
    __completed = False

    @abstractmethod
    def update(self):
        pass

    def setCompleted(self, c):
        self.__completed = c
        self.completeChanged.emit()

    def isComplete(self):
        return self.__completed
