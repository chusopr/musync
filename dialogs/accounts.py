from dialogs.sources import SourcesDialog
from modules import SourceModule

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QComboBox
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import pyqtSignal

class AccountsDialog(QDialog):
    __source_name = None
    account_added = pyqtSignal(SourceModule)
    account_deleted = pyqtSignal(str)
    account_selected = pyqtSignal(SourceModule)

    def __del_account(self, source_name, accountsList):
        self.account_deleted.emit(accountsList.selectedItems()[0].source.getId())
        accountsList.selectedItems()[0].source.deleteAccount()
        accountsList.takeItem(accountsList.currentRow())

    def __add_account(self, account):
        accountItem = QListWidgetItem(account.getName())
        accountItem.source = account
        self.findChild(QListWidget, "accountsList").addItem(accountItem)
        self.account_added.emit(account)

    def __show_modules(self, accounts):
        sourcesDialog = SourcesDialog(self, accounts)
        sourcesDialog.account_added.connect(self.__add_account)

    def __select_account(self, source_name, accountsList):
        account = accountsList.selectedItems()[0].source
        self.account_selected.emit(account)
        self.close()

    def __init__(self, accounts, source_name):
        super().__init__()
        self.setWindowTitle("muSync - Accounts")
        self.setModal(True)
        
        dialogLayout = QVBoxLayout(self)

        accountsList = QListWidget()
        accountsList.setObjectName("accountsList")
        dialogLayout.addWidget(accountsList)

        buttonsLayout = QHBoxLayout()
        addButton = QPushButton(QIcon.fromTheme("list-resource-add"), "&Add account")
        addButton.clicked.connect(lambda: self.__show_modules(accounts))
        buttonsLayout.addWidget(addButton)
        delButton = QPushButton(QIcon.fromTheme("edit-delete"), "&Remove account")
        delButton.clicked.connect(lambda: self.__del_account(source_name, accountsList))
        delButton.setDisabled(True)
        buttonsLayout.addWidget(delButton)
        okButton = QPushButton(QIcon.fromTheme("dialog-ok"), "&Select source")
        okButton.clicked.connect(lambda: self.__select_account(source_name, accountsList))
        okButton.setDisabled(True)
        buttonsLayout.addWidget(okButton)
        cancelButton = QPushButton(QIcon.fromTheme("dialog-cancel"), "&Cancel")
        cancelButton.clicked.connect(self.close)
        buttonsLayout.addWidget(cancelButton)
        dialogLayout.addLayout(buttonsLayout)
        accountsList.itemSelectionChanged.connect(lambda: okButton.setDisabled(True if accountsList.selectedIndexes() == [] else False))
        accountsList.itemSelectionChanged.connect(lambda: delButton.setDisabled(True if accountsList.selectedIndexes() == [] else False))

        for account in accounts.values():
            sourceItem = QListWidgetItem(account.getName())
            sourceItem.source = account
            accountsList.addItem(sourceItem)

        accountsList.itemDoubleClicked.connect(lambda: self.__select_account(source_name, accountsList))
        self.show()