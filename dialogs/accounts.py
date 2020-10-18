from dialogs.sources import SourcesDialog

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QPushButton
from PyQt5.QtGui import QIcon

class AccountsDialog(QDialog):
    __parent = None
    __source_name = None

    def __del_account (self, source_name, accountsList):
        del self.__parent._accounts[accountsList.selectedItems()[0].source.getId()]
        accountsList.selectedItems()[0].source.deleteAccount()
        accountsList.takeItem(accountsList.currentRow())
        self.__parent._save_settings()

    def __add_account(self, source_name, accountsList):
        self.__parent._change_account(source_name, accountsList)
        self.close()

    def __init__(self, parent, source_name):
        self.__parent = parent
        super().__init__()
        self.setWindowTitle("muSync - Accounts")
        self.setModal(True)
        
        dialogLayout = QVBoxLayout(self)

        accountsList = QListWidget()
        dialogLayout.addWidget(accountsList)

        buttonsLayout = QHBoxLayout()
        addButton = QPushButton(QIcon.fromTheme("list-resource-add"), "&Add account")
        addButton.clicked.connect(lambda: SourcesDialog(self.__parent, accountsList))
        buttonsLayout.addWidget(addButton)
        delButton = QPushButton(QIcon.fromTheme("edit-delete"), "&Remove account")
        delButton.clicked.connect(lambda: self.__del_account(source_name, accountsList))
        delButton.setDisabled(True)
        buttonsLayout.addWidget(delButton)
        okButton = QPushButton(QIcon.fromTheme("dialog-ok"), "&Select source")
        okButton.clicked.connect(lambda: self.__add_account(source_name, accountsList))
        okButton.setDisabled(True)
        buttonsLayout.addWidget(okButton)
        cancelButton = QPushButton(QIcon.fromTheme("dialog-cancel"), "&Cancel")
        cancelButton.clicked.connect(self.close)
        buttonsLayout.addWidget(cancelButton)
        dialogLayout.addLayout(buttonsLayout)
        accountsList.itemSelectionChanged.connect(lambda: okButton.setDisabled(True if accountsList.selectedIndexes() == [] else False))
        accountsList.itemSelectionChanged.connect(lambda: delButton.setDisabled(True if accountsList.selectedIndexes() == [] else False))

        for account in self.__parent._accounts.values():
            sourceItem = QListWidgetItem(account.getName())
            sourceItem.source = account
            accountsList.addItem(sourceItem)

        accountsList.itemDoubleClicked.connect(lambda: self.__add_account(source_name, accountsList))
        self.show()
