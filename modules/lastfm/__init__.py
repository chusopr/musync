import json
import re
from math import ceil
from hashlib import md5
from PySide6.QtCore import QUrl
from dialogs.browser import Browser

import modules


class SourceModule(modules.SourceModule):
    __id = "lastfm"
    __name = "Last.fm"
    # Get your API key from https://www.last.fm/api/account/create
    __api_key = None
    __api_secret = None
    __session_key = None

    __login_url = "https://last.fm/api/account/create"

    __username = None

    def __lastfm_createform_ready(self, browser):
        if browser.get_url().toString(QUrl.PrettyDecoded | QUrl.RemoveFragment) != "https://www.last.fm/api/account/create":
            return False

        if browser.run_js("document.getElementById('id_name') == null"):
            return False

        if browser.run_js("typeof grecaptcha != 'object'"):
            return False
        if browser.run_js("typeof grecaptcha.enterprise != 'object'"):
            return False
        if browser.run_js("typeof grecaptcha.enterprise.getResponse != 'function'"):
            return False

        if browser.run_js("grecaptcha.enterprise.getResponse()"):
            return True
        elif browser.get_url().fragment() != 'id_homepage':
            msg = modules.MessageBox(modules.MessageBox.Information, "CAPTCHA required", "Please check the ReCAPTCHA checkbox in Last.fm form to confirm that you are not a robot", modules.MessageBox.Ok, browser)
            msg.setModal(True)
            msg.exec()
            browser.run_js('window.location.hash = "id_homepage"')
        return False

    def __lastfm_apitable_ready(self, browser):
        return browser.run_js("""document.getElementsByClassName("auth-dropdown-menu-item").length > 0 &&
            document.getElementsByClassName("api-details-table").length > 0""")

    def __lastfm_authtoken_success(self, browser):
        return browser.run_js('document.getElementsByClassName("alert-success").length == 1')

    def __save_cache(self):
        try:
            modules.keyring.set_password("muSync", self.__id, json.dumps([self.__api_key, self.__api_secret, self.__session_key]))
        except Exception as e:
            print("Failed to cache session data: {}".format(str(e)))

    def initialize(self):
        if not self.__id == "lastfm":
            try:
                self.__username = re.sub(r"lastfm-", "", self.__id)
                self.__name = "{}'s Last.fm account".format(self.__username)
                credentials = json.loads(modules.keyring.get_password("muSync", self.__id))
                self.__api_key = credentials[0]
                self.__api_secret = credentials[1]
                if len(credentials) == 3:
                    self.__session_key = credentials[2]
                self.__authenticated = True
            except Exception as e:
                print("Need to re-authenticate: {}".format(str(e)))

    def __track_metadata(self, d):
        track = {}
        track["artist"] = ""
        if "artist" in d:
            if "name" in d["artist"]:
                track["artist"] = d["artist"]["name"]
            elif "#text" in d["artist"]:
                track["artist"] = d["artist"]["#text"]
        track["title"] = d["name"] if "name" in d else ""
        return track

    def isAuthenticated(self):
        return self.__authenticated and self.__session_key is not None

    def __get_session_key(self, browser):
        if self.__session_key is not None:
            return self.__session_key

        token_request = modules.requests.get("http://ws.audioscrobbler.com/2.0/?method=auth.getToken&api_key={}&api_sig={}&format=json".format(
            self.__api_key,
            md5(f"api_key{self.__api_key}methodauth.getToken{self.__api_secret}".encode("utf-8")).hexdigest()
        ), timeout=30)

        try:
            token_request_json = json.loads(token_request.text)
        except Exception:
            return False

        if token_request.status_code != 200 or "token" not in token_request_json:
            self.status.emit("Error authenticating to Last.fm")
            return False

        auth_token = token_request_json["token"]

        browser.show()
        browser.get(f"http://www.last.fm/api/auth/?api_key={self.__api_key}&token={auth_token}")

        browser.wait(self.__lastfm_authtoken_success)

        browser.accept()

        session_request = modules.requests.get("http://ws.audioscrobbler.com/2.0/?method=auth.getsession&api_key={}&token={}&api_sig={}&format=json".format(
            self.__api_key,
            auth_token,
            md5(f"api_key{self.__api_key}methodauth.getsessiontoken{auth_token}{self.__api_secret}".encode("utf-8")).hexdigest()
        ), timeout=30)

        try:
            session_request_json = json.loads(session_request.text)
        except Exception:
            return False

        if session_request.status_code != 200 or "session" not in session_request_json or "key" not in session_request_json["session"]:
            self.status.emit("Error authenticating to Last.fm")
            return False

        self.__session_key = session_request_json["session"]["key"]

        return self.__session_key

    def authenticate(self, force=False, parent=None):
        browser = Browser(parent)
        if not self.__authenticated or force:

            browser.get(self.__login_url)
            browser.show()

            if not browser.wait(self.__lastfm_createform_ready):
                browser.reject()
                browser.deleteLater()
                self.__authenticated = False
                return False

            browser.run_js('document.getElementById("id_homepage").value = "https://musync.link"')
            browser.run_js('document.getElementById("id_name").value = "muSync"')

            browser.run_js('document.getElementById("id_name").form.submit()')

            browser.wait(self.__lastfm_apitable_ready)

            self.__username = browser.run_js('document.getElementsByClassName("username")[0].textContent')
            self.__api_key = browser.run_js('document.getElementsByClassName("api-details-table")[0].rows[1].cells[1].textContent')
            self.__api_secret = browser.run_js('document.getElementsByClassName("api-details-table")[0].rows[2].cells[1].textContent')
            browser.accept()

            try:
                userinfo_request = modules.requests.get(f"http://ws.audioscrobbler.com/2.0/?method=user.getinfo&user={self.__username}&api_key={self.__api_key}&format=json", timeout=30)
                if userinfo_request.status_code != 200:
                    browser.deleteLater()
                    return False  # TODO do something
                userinfo = json.loads(userinfo_request.text)
            except Exception:
                browser.deleteLater()
                return False

            if not (userinfo and "user" in userinfo and "name" in userinfo["user"]):
                browser.deleteLater()
                return False  # TODO do something

            self.__name = "{}'s Last.fm account".format(userinfo["user"]["name"])
            self.__id = "lastfm-{}".format(self.__username)

            self.__authenticated = True

        if not self.__get_session_key(browser):
            browser.deleteLater()
            return False

        browser.deleteLater()
        self.__save_cache()

        return True

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

    def getTracks(self, playlist_name, cancel):
        tracks = []
        current_page = 1
        total_pages = 1
        while current_page <= total_pages:
            if cancel.is_set():
                self.log.emit(f"Loading tracks for {playlist_name} playlist in Last.fm account {self.__username} was cancelled")
                return
            tracks_request = modules.requests.get(f"http://ws.audioscrobbler.com/2.0/?method=user.get{playlist_name}tracks&user={self.__username}&api_key={self.__api_key}&format=json&page={current_page}", timeout=30)

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
            self.status.emit("Please wait while the list of songs is being downloaded ({} % completed).".format(round(100 * current_page / total_pages)))
            current_page = current_page + 1

        self.status.emit("Finished loading tracks")

        return tracks

    def searchTrack(self, track):
        tracks = []
        current_page = 1
        total_pages = 1
        # Last.fm allows scrobbling or faving tracks that don't exist in their
        # catalog, which will auto-create them, so we always give the choice to
        # add the song with the same verbatim name it has in the other source,
        # unless a verbatim result was already found in their catalog
        verbatim_found = False

        while current_page <= total_pages:
            search_request = modules.requests.get("http://ws.audioscrobbler.com/2.0/", params={
                "method": "track.search",
                "artist": track["search_artist"] if "search_artist" in track and track["search_artist"] != "" else track["artist"],
                "track": track["search_title"]  if "search_title"  in track and track["search_title"]  != "" else track["title"],
                "api_key": self.__api_key,
                "format": "json",
                "page": current_page
            }, timeout=30)

            if search_request.status_code != 200:
                self.status.emit("Error searching for tracks")
                break

            search_results = json.loads(search_request.text)

            for d in search_results["results"]["trackmatches"]["track"]:
                tracks.append({
                    "artist": d["artist"],
                    "title":  d["name"]
                })
                # Check if this seach result matches the same exact name as in the other source
                # so we don't need to explicitly add the verbatim result to the returned search results.
                # We make the comparison case insensitive because Last.fm is case insensitive.
                if (track["artist"].lower() == d["artist"].lower() and track["title"].lower() == d["name"].lower()):
                    verbatim_found = True

            total_pages = ceil(float(search_results["results"]["opensearch:totalResults"]) / int(search_results["results"]["opensearch:itemsPerPage"]))
            current_page = current_page + 1
            # Get only one page for now
            break

        if not verbatim_found:
            tracks.append({
                "artist": track["artist"],
                "title":  track["title"]
            })

        return tracks

    def addTrack(self, playlist, track):
        if playlist["id"] == "loved":

            love_request = modules.requests.post("http://ws.audioscrobbler.com/2.0/", data={
                "method": "track.love",
                "track": track["title"],
                "artist": track["artist"],
                "api_key": self.__api_key,
                "sk": self.__session_key,
                "api_sig": md5(f"api_key{self.__api_key}artist{track['artist']}methodtrack.lovesk{self.__session_key}track{track['title']}{self.__api_secret}".encode("utf-8")).hexdigest(),
                "format": "json"
            }, timeout=30)

            if love_request.status_code == 200:
                return True

            self.log.emit("Failed to add {} - {} to {} playlist in {}: {}".format(track["artist"], track["title"], playlist["name"], self.__name, love_request.text))

        return False
