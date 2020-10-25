from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QHBoxLayout, QLineEdit, QDialogButtonBox, QMessageBox
import requests, modules, json, os, re
from appdirs import user_cache_dir
from math import ceil
from modules.lastfm.auth import AuthDialog

class SourceModule(modules.SourceModule):
    __id = "lastfm"
    __name = "Last.fm"
    # Get your API key from https://www.last.fm/api/account/create
    __api_key = ""

    __username = None
    __session_file = os.path.join(user_cache_dir("musync"), "{}.session".format(__id))

    def initialize(self):
        if not self.__id == "lastfm":
            self.__username = re.sub(r"lastfm-", "", self.__id)
            self.__id = "lastfm-{}".format(self.__username)
            self.__name = "{}'s Last.fm account".format(self.__username)

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

    def isAuthenticated(self):
        return self.__username is not None

    def authenticate(self, force=False):
        if self.__username is not None:
            return True
        authDialog = AuthDialog(self.__api_key)
        if authDialog.exec() == QDialog.Accepted:
            self.__id = "lastfm-{}".format(authDialog.getUser())
            self.initialize()
            return True
        return False

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
            self.status.emit("Please wait while the list of songs is being downloaded ({} % completed).".format(round(100*current_page/total_pages)))
            current_page = current_page + 1

        self.status.emit("Finished loading tracks")

        return tracks

    def searchTrack(self, track):
        tracks = []
        current_page = 1
        total_pages = 1

        while current_page <= total_pages:
            search_request = requests.get("http://ws.audioscrobbler.com/2.0/?method=track.search&artist={}&track={}&api_key={}&format=json&page={}".format(
                track["search_artist"] if "search_artist" in track and track["search_artist"] != "" else track["artist"],
                track["search_title"]  if "search_title"  in track and track["search_title"]  != "" else track["title"],
                self.__api_key, current_page
            ))

            if search_request.status_code != 200:
                self.status.emit("Error searching for tracks")
                break

            search_results = json.loads(search_request.text)

            for d in search_results["results"]["trackmatches"]["track"]:
                tracks.append({
                    "artist": d["artist"],
                    "title":  d["name"],
                    "id":     d["url"]
                })

            total_pages = ceil(float(search_results["results"]["opensearch:totalResults"])/int(search_results["results"]["opensearch:itemsPerPage"]))
            current_page = current_page + 1
            # Get only one page for now
            break

            if (
                    "{}tracks".format(playlist_name) not in playlist or
                    "track" not in playlist["{}tracks".format(playlist_name)]
            ):
                break

            for t in playlist["{}tracks".format(playlist_name)]["track"]:
                tracks.append(self.__track_metadata(t))
            total_pages = int(playlist["{}tracks".format(playlist_name)]["@attr"]["totalPages"])
            self.status.emit("Please wait while the list of songs is being downloaded ({} % completed).".format(round(100*current_page/total_pages)))
            current_page = current_page + 1

        return tracks

    #def addTrack(self, track):
        #search_request = requests.get("http://ws.audioscrobbler.com/2.0/?method=track.search&artist={}&track={}&api_key={}&format=json&page={}".format(
            #track["search_artist"] if "search_artist" in track and track["search_artist"] != "" else track["artist"],
            #track["search_title"]  if "search_title"  in track and track["search_title"]  != "" else track["title"],
            #self.__api_key, current_page
        #))

        #if search_request.status_code != 200:
            #self.status.emit("Error searching for tracks")
            #break

        #search_results = json.loads(search_request.text)
