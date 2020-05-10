from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QHBoxLayout, QLineEdit, QDialogButtonBox, QMessageBox
from PyQt5.QtCore import Qt
import requests, modules, json, os
from appdirs import user_cache_dir

class SourceModule(modules.SourceModule):
    __id = "lastfm"
    __name = "Last.fm"
    # Get your API key from https://www.last.fm/api/account/create
    __api_key = ""

    __username = None
    __session_file = os.path.join(user_cache_dir("musync"), "{}.session".format(__id))

    def initialize(self):
        if (os.path.isfile(self.__session_file)):
            try:
                with open(self.__session_file, "r") as f:
                    self.__domain, self.__cookies, self.__amzn = json.load(f)
                requests.utils.add_dict_to_cookiejar(self.__session.cookies, self.__cookies)
                self.__authenticated = True

            except Exception as e:
                print("Need to re-authenticate: {}".format(str(e)))

    def __http_debug(self):
        import http.client as http_client
        import logging
        http_client.HTTPConnection.debuglevel = 1
        logging.basicConfig()
        logging.getLogger().setLevel(logging.DEBUG)
        requests_log = logging.getLogger("requests.packages.urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True

    def __track_metadata(self, d):
        track = {}
        track["artist"] = d["artist"]["name"] if "artist" in d and "name" in d["artist"] else ""
        track["title"] = d["name"] if "name" in d else ""
        return track

    def __reject_auth(self, authDialog):
        authDialog.reject()

    def __login(self, authDialog, username):
        r = requests.get("http://ws.audioscrobbler.com/2.0/?method=user.getinfo&user={}&api_key={}&format=json".format(username, self.__api_key))

        if r.status_code != 200:
            authDialog.reject()
            return None

        self.__username = username
        authDialog.accept()
        return True

    def isAuthenticated(self):
        return self.__username is not None

    def authenticate(self, window, force=False):
        if self.__username is not None:
            return True
        authDialog = QDialog(window)
        authLayout = QVBoxLayout(authDialog)

        authLabel = QLabel("Please provide your %s account name" % self.__name, authDialog)

        authLayout.addWidget(authLabel)

        userLayout = QHBoxLayout()

        userLayout.addWidget(QLabel("Username:", authDialog))
        userInput = QLineEdit(authDialog)
        userLayout.addWidget(userInput)

        authLayout.addLayout(userLayout)

        buttonBox = QDialogButtonBox(authDialog);
        buttonBox.setOrientation(Qt.Horizontal)
        buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok);

        authLayout.addWidget(buttonBox);

        buttonBox.accepted.connect(lambda: self.__login(authDialog, userInput.text()))
        buttonBox.rejected.connect(lambda: self.__reject_auth(authDialog))
        return True if authDialog.exec() == QDialog.Accepted else False

    def getPlaylists(self):
        return [
            {
                "id": "recent",
                "name": "Recent tracks",
                "writable": True
            },
            {
                "id": "loved",
                "name": "Loved tracks",
                "writable": True
            }
        ]

    def getTracks(self, playlist_name):

        tracks = []
        current_page = 1
        total_pages = 1
        while current_page <= total_pages:
            tracks_request = requests.get("http://ws.audioscrobbler.com/2.0/?method=user.get{}tracks&user={}&api_key={}&format=json&page={}".format(playlist_name, self.__username, self.__api_key, current_page))

            if tracks_request.status_code != 200:
                break
            playlist = json.loads(tracks_request.text)

            if (
                    "{}tracks".format(playlist_name) not in playlist or
                    "track" not in playlist["{}tracks".format(playlist_name)]
            ):
                break

            for t in playlist["{}tracks".format(playlist_name)]["track"]:
                tracks.append(self.__track_metadata(t))
            total_pages = int(playlist["{}tracks".format(playlist_name)]["@attr"]["totalPages"])
            self.__main.statusBar().showMessage("Please wait while the list of songs is being downloaded ({} % completed).".format(round(100*current_page/total_pages)))
            current_page = current_page + 1

        self.__main.statusBar().showMessage("Finished loading tracks")

        return tracks
