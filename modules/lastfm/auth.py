from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit
from PyQt5.QtCore import Qt
import requests

class AuthDialog(QDialog):
    __api_key = ""
    __username = ""

    def getUser(self):
        return self.__username

    def __reject_auth(self):
        self.reject()

    def __login(self, authDialog, username):
        r = requests.get("http://ws.audioscrobbler.com/2.0/?method=user.getinfo&user={}&api_key={}&format=json".format(username, self.__api_key))

        if r.status_code != 200:
            self.reject()
            return None

        self.__username = username
        authDialog.accept()
        return True

    def __init__(self, api_key):
        super().__init__()
        self.__api_key = api_key

        authLayout = QVBoxLayout(self)

        authLabel = QLabel("Please provide your Last.fm account name", self)
        authLayout.addWidget(authLabel)

        userLayout = QHBoxLayout()
        userLayout.addWidget(QLabel("Username:", self))
        userInput = QLineEdit(self)
        userLayout.addWidget(userInput)
        authLayout.addLayout(userLayout)

        buttonBox = QDialogButtonBox(self);
        buttonBox.setOrientation(Qt.Horizontal)
        buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok);

        authLayout.addWidget(buttonBox);

        buttonBox.accepted.connect(lambda: self.__login(self, userInput.text()))
        buttonBox.rejected.connect(self.__reject_auth)
