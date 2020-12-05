import modules

from PySide2.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QPushButton
from PySide2.QtGui import QIcon
from PySide2.QtCore import QSettings, Signal

class SourcesDialog(QDialog):
    account_added = Signal(modules.SourceModule)

    def __add_account(self, sourcesList):
        module_name = sourcesList.currentItem().text()
        module_slug = sourcesList.currentItem().slug

        if not module_slug in modules.modules:
            pass # TODO

        account = modules.create_object(module_slug)

        if not account.authenticate():
            # TODO do something else than failing silently
            return False

        accounts = QSettings()
        accounts.beginGroup("accounts")
        if account.getId() in accounts.childKeys():
            errorMsg = QMessageBox(QMessageBox.Critical, "Account already exists", "This account already exists. Please delete it first.", QMessageBox.Ok, self)
            errorMsg.show()
            return

        self.account_added.emit(account)
        self.close()

    def __init__(self, parent):
        super().__init__()
        self.setWindowTitle("muSync - Sources")
        self.setModal(True)
        dialogLayout = QVBoxLayout(self)
        sourcesList = QListWidget()
        dialogLayout.addWidget(sourcesList)
        buttonsLayout = QHBoxLayout()
        okButton = QPushButton(QIcon.fromTheme("dialog-ok"), "&Ok")
        okButton.clicked.connect(lambda: self.__add_account(sourcesList))
        okButton.setDisabled(True)
        buttonsLayout.addWidget(okButton)
        cancelButton = QPushButton(QIcon.fromTheme("dialog-cancel"), "&Cancel")
        cancelButton.clicked.connect(self.close)
        buttonsLayout.addWidget(cancelButton)
        dialogLayout.addLayout(buttonsLayout)
        for source in modules.modules.items():
            sourceItem = QListWidgetItem(source[1])
            sourceItem.slug = source[0]
            sourcesList.addItem(sourceItem)
        sourcesList.itemSelectionChanged.connect(lambda: okButton.setDisabled(True if sourcesList.selectedIndexes() == [] else False))
        sourcesList.itemDoubleClicked.connect(lambda: self.__add_account(sourcesList))
        self.show()

