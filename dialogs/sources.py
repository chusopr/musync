import modules

from PyQt5.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QPushButton
from PyQt5.QtGui import QIcon

class SourcesDialog(QDialog):
    __parent = None

    def __add_account(self, sourceDialog, sourcesList, accountsList):
        module_name = sourcesList.currentItem().text()
        module_slug = sourcesList.currentItem().slug

        if not module_slug in modules.modules:
            self.__parent()._bogus_module(module_name)
            return

        source = modules.create_object(self.__parent, module_slug)

        if not source.authenticate(self.__parent):
            return False

        if source.getId() in self.__parent._accounts.keys():
            errorMsg = QMessageBox(QMessageBox.Critical, "Account already exists", "This account already exists. Please delete it first.", QMessageBox.Ok, self)
            errorMsg.show()
            return
        self.__parent._accounts[source.getId()] = source

        accountItem = QListWidgetItem(source.getName())
        accountItem.source = source
        accountsList.addItem(accountItem)
        sourceDialog.close()
        self.__parent._save_settings()

    def __init__(self, parent, accountsList):
        super().__init__()
        self.__parent = parent
        sourceDialog = QDialog(parent)
        sourceDialog.setWindowTitle("muSync - Sources")
        sourceDialog.setModal(True)
        dialogLayout = QVBoxLayout(sourceDialog)
        sourcesList = QListWidget()
        dialogLayout.addWidget(sourcesList)
        buttonsLayout = QHBoxLayout()
        okButton = QPushButton(QIcon.fromTheme("dialog-ok"), "&Ok")
        okButton.clicked.connect(lambda: self.__add_account(sourceDialog, sourcesList, accountsList))
        okButton.setDisabled(True)
        buttonsLayout.addWidget(okButton)
        cancelButton = QPushButton(QIcon.fromTheme("dialog-cancel"), "&Cancel")
        cancelButton.clicked.connect(sourceDialog.close)
        buttonsLayout.addWidget(cancelButton)
        dialogLayout.addLayout(buttonsLayout)
        for source in modules.modules.items():
            sourceItem = QListWidgetItem(source[1])
            sourceItem.slug = source[0]
            sourcesList.addItem(sourceItem)
        sourcesList.itemSelectionChanged.connect(lambda: okButton.setDisabled(True if sourcesList.selectedIndexes() == [] else False))
        sourcesList.itemDoubleClicked.connect(lambda: self.__add_account(sourceDialog, sourcesList, accountsList))
        sourceDialog.show()

