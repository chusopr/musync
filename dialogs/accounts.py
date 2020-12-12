from dialogs.sources import SourcesDialog
import modules

from PySide2.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QPushButton
from PySide2.QtGui import QIcon
from PySide2.QtCore import QSettings, Signal, Slot

class AccountsDialog(QDialog):
    account_added = Signal(modules.SourceModule)
    account_deleted = Signal(str)
    account_selected = Signal(modules.SourceModule)

    @Slot(bool)
    def __del_account(self, accountsList):
        account = accountsList.selectedItems()[0].account
        self.account_deleted.emit(account.getId())
        QSettings().remove("accounts/{}".format(account.getId()))
        account.deleteAccount()
        accountsList.takeItem(accountsList.currentRow())

    @Slot(modules.SourceModule)
    def __add_account(self, account):
        accountItem = QListWidgetItem(account.getName())
        accountItem.account = account
        self.findChild(QListWidget, "accountsList").addItem(accountItem)
        QSettings().setValue("accounts/{}".format(account.getId()), account.getType())
        self.account_added.emit(account)

    @Slot(bool)
    def __show_modules(self):
        sourcesDialog = SourcesDialog(self)
        sourcesDialog.account_added.connect(self.__add_account)
        del sourcesDialog

    @Slot(bool)
    @Slot(QListWidgetItem)
    def __select_account(self, accountsList):
        account = accountsList.selectedItems()[0].account
        self.account_selected.emit(account)
        self.close()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("muSync - Accounts")
        self.setModal(True)
        
        dialogLayout = QVBoxLayout(self)

        accountsList = QListWidget()
        accountsList.setObjectName("accountsList")
        dialogLayout.addWidget(accountsList)

        buttonsLayout = QHBoxLayout()
        addButton = QPushButton(QIcon.fromTheme("list-resource-add"), "&Add account")
        addButton.clicked.connect(lambda: self.__show_modules())
        buttonsLayout.addWidget(addButton)
        delButton = QPushButton(QIcon.fromTheme("edit-delete"), "&Remove account")
        delButton.clicked.connect(lambda: self.__del_account(accountsList))
        delButton.setDisabled(True)
        buttonsLayout.addWidget(delButton)
        okButton = QPushButton(QIcon.fromTheme("dialog-ok"), "&Select account")
        okButton.clicked.connect(lambda: self.__select_account(accountsList))
        okButton.setDisabled(True)
        buttonsLayout.addWidget(okButton)
        cancelButton = QPushButton(QIcon.fromTheme("dialog-cancel"), "&Cancel")
        cancelButton.clicked.connect(self.close)
        buttonsLayout.addWidget(cancelButton)
        dialogLayout.addLayout(buttonsLayout)
        accountsList.itemSelectionChanged.connect(lambda: okButton.setDisabled(True if accountsList.selectedIndexes() == [] else False))
        accountsList.itemSelectionChanged.connect(lambda: delButton.setDisabled(True if accountsList.selectedIndexes() == [] else False))

        accounts = QSettings()
        accounts.beginGroup("accounts")
        for account_id in accounts.childKeys():
            module_name = accounts.value(account_id)

            if not module_name in modules.modules:
                pass # TODO

            account = modules.create_object(module_name)
            account.setId(account_id)
            account.initialize()

            accountListItem = QListWidgetItem(account.getName())
            accountListItem.account = account
            accountsList.addItem(accountListItem)

        accountsList.itemDoubleClicked.connect(lambda: self.__select_account(accountsList))
        self.show()
