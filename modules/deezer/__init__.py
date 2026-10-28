from dialogs.browser import Browser
import json
import re
from html import escape

import modules


class SourceModule(modules.SourceModule):
    __id = "deezer"
    __name = "Deezer"
    __login_url = "https://account.deezer.com"
    __cookie_domain_regexp = re.compile(r"\.deezer.com$")
    __loved_playlist = None

    def __save_cache(self):
        try:
            modules.keyring.set_password("muSync",
                                         self.__id, json.dumps(self.__cookies))
        except Exception as e:
            print("Failed to cache session data: {}".format(str(e)))

    def initialize(self):
        self.__session = modules.requests.Session()
        self.__authenticated = False
        self.__cookies = {}
        self.__user_id = self.__api_token = ""
        if not self.__id == "deezer":
            try:
                self.__user_id = re.sub(r"deezer-", "", self.__id)
                self.__cookies = json.loads(
                    modules.keyring.get_password("muSync", self.__id))
                self.__authenticated = self.__get_session_key() and self.__set_profile()
            except Exception as e:
                self.__authenticated = False
                print("Need to re-authenticate: {}".format(str(e)))

    def isAuthenticated(self):
        return self.__authenticated

    def __cookies_ready(self, browser):
        arl = sid = None
        for d, cookies in browser.get_cookies().items():
            if self.__cookie_domain_regexp.search(d):
                if "arl" in cookies:
                    arl = cookies["arl"]["value"]
                if "sid" in cookies:
                    sid = cookies["sid"]["value"]
        if arl and sid:
            return {"arl": arl, "sid": sid}

    def __request(self, method, data={}, redirected=False):
        if not (
            self.__authenticated and "arl" in self.__cookies
        ):
            return None

        try:
            if data == {}:
                r = self.__session.get(f"https://www.deezer.com/ajax/gw-light.php?method={method}&api_version=1.0&api_token={self.__api_token}", timeout=30)
            else:
                r = self.__session.post(f"https://www.deezer.com/ajax/gw-light.php?method={method}&api_version=1.0&api_token={self.__api_token}", json=data, timeout=30)
        except Exception as e:
            self.log.emit(escape(str(e)))
            return None

        try:
            r_json = r.json()
        except Exception as e:
            self.log.emit(escape(str(e)))
            return None

        if r.status_code in [401, 400, 403] or (
            r_json["error"] and "VALID_TOKEN_REQUIRED" in r_json["error"]
        ):
            if redirected:
                self.log.emit(escape(r.text))
                return None
            else:
                if not self.__get_session_key():
                    return None
                return self.__request(method, data, redirected=True)
        return r

    def __set_profile(self):
        r = self.__request(
            method="deezer.pageProfile",
            data={"user_id": self.__user_id, "tab": "home", "nb": 10000}
        )

        if not r or r.status_code != 200 or r.json()["error"]:
            self.status.emit("Error loading Deezer profile")
            if r is not None:
                self.log.emit(escape(r.text))
            return False

        userinfo = r.json()
        if (
            "results" not in userinfo or
            "DATA" not in userinfo["results"] or
            "USER" not in userinfo["results"]["DATA"] or
            "DISPLAY_NAME" not in userinfo["results"]["DATA"]["USER"]
        ):
            self.status.emit("Error getting Deezer user details")
            return False

        self.__username = userinfo["results"]["DATA"]["USER"]["DISPLAY_NAME"]
        self.__name = f"{self.__username}'s Deezer account"

        self.__playlists = {}
        if "LOVEDTRACKS_ID" in userinfo["results"]["DATA"]["USER"]:
            self.__loved_playlist = userinfo["results"]["DATA"]["USER"]["LOVEDTRACKS_ID"]
            self.__playlists[self.__loved_playlist] = {
                "name": "Favourite tracks",
                "writable": True
            }

        if (
            "TAB" in userinfo["results"] and
            "home" in userinfo["results"]["TAB"] and
            "playlists" in userinfo["results"]["TAB"]["home"] and
            "data" in userinfo["results"]["TAB"]["home"]["playlists"]
        ):
            for pl in userinfo["results"]["TAB"]["home"]["playlists"]["data"]:
                # TODO Can we add tracks to someone else's playlist?
                self.__playlists[pl["PLAYLIST_ID"]] = {
                    "name": pl["TITLE"],
                    "writable": pl["PARENT_USER_ID"] == self.__user_id
                }

        return True

    def __get_session_key(self):
        # Temporarily set to True so we can use self.__request()
        self.__authenticated = True
        for n, v in self.__cookies.items():
            self.__session.cookies.set(n, v, domain=".deezer.com")
        r = self.__request("deezer.getUserData", redirected=True)
        try:
            userinfo = r.json()
            if int(userinfo["results"]["USER"]["USER_ID"]) == 0:
                self.__authenticated = False
                return False
            self.__user_id = str(userinfo["results"]["USER"]["USER_ID"])
            self.__api_token = userinfo["results"]["checkForm"]
            self.__id = f"deezer-{self.__user_id}"
        except Exception as e:
            self.__authenticated = False
            self.status.emit("Error getting Deezer user details")
            self.log.emit(escape(str(e)))
            return False

        return True

    def authenticate(self, force=False, parent=None):
        if not self.__authenticated or force:
            browser = Browser(parent)
            browser.get(self.__login_url)
            browser.show()

            self.__user_id = self.__api_token = ""
            self.__cookies = {}

            self.__cookies = browser.wait(self.__cookies_ready)
            browser.accept()
            browser.deleteLater()
            if not self.__cookies:
                self.status.emit("Authentication to Deezer cancelled")
                return False

            previous_id = self.__id
            if not self.__get_session_key():
                self.__authenticated = False
                return False

            if self.__id != previous_id and previous_id != "deezer":
                self.status.emit("Authenticated as a different user. If you want to add a new Deezer account, use the Add Account button.")
                self.__id = previous_id
                self.__authenticated = False
                return False

            if not self.__set_profile():
                self.__authenticated = False
                return False

            self.__save_cache()
        return True

    def getPlaylists(self):
        self.__set_profile()
        if not isinstance(self.__playlists, dict):
            return

        return [{
            "id": k,
            "name": v["name"],
            "writable": v["writable"]
        } for k, v in self.__playlists.items()]

    def __tracks_metadata(self, trackList):
        if "results" not in trackList or "data" not in trackList["results"]:
            return None

        tracks = []
        for t in trackList["results"]["data"]:
            artist = ""
            if "ART_NAME" in t:
                artist = t["ART_NAME"]
            elif "ARTISTS" in t:
                artist = ", ".join([a["ART_NAME"] for a in t["ARTISTS"]])
            tracks.append({
                "id": t["SNG_ID"],
                "artist": artist,
                "title": t["SNG_TITLE"]
            })
        return tracks

    def getTracks(self, playlist_id, cancel):
        total = 1
        count = 0
        tracks = []
        while count < total:
            trackList = self.__request(
                method="playlist.getSongs",
                data={"playlist_id": playlist_id, "start": count, "nb": 10000}
            )
            if not trackList:
                return False

            if cancel.is_set():
                return

            trackList = trackList.json()

            try:
                total = trackList["results"]["total"]
                if total == 0:
                    # Empty playlist
                    return tracks
                count += trackList["results"]["count"]
            except Exception as e:
                self.status.emit(f"Failed loading playlist {self.__playlists[playlist_id]['name']}")
                self.log.emit(escape(str(e)))
                return None

            next_tracks = self.__tracks_metadata(trackList)
            if not next_tracks:
                self.status.emit(f"Cannot complete {self.__playlists[playlist_id]['name']} playlist download in {self.__name}")
                return
            tracks += next_tracks

            self.status.emit("Please wait while the list of songs is being downloaded ({} % completed).".format(round(100 * (count) / total)))

        if cancel.is_set():
            self.log.emit(f"Loading tracks for {self.__playlists[playlist_id]['name']} playlist in Deezer account {self.__username} was cancelled")
            return

        self.status.emit("Finished loading tracks")
        return tracks

    def searchTrack(self, track):
        query = track["search_artist"] if "search_artist" in track and track["search_artist"] != "" else track["artist"]
        if query != "":
            query += " "
        query += track["search_title"] if "search_title" in track and track["search_title"] != "" else track["title"]

        search_results = self.__request(
            method="search.music",
            data={
                "query": query,
                "filter": "ALL",
                "output": "TRACK",
                "start": 0,
                "nb": 20
            }
        )

        try:
            search_results = search_results.json()
        except Exception as e:
            self.status.emit(f"Failed loading search results for {escape(query)}")
            self.log.emit(escape(str(e)))
            return None

        tracks = self.__tracks_metadata(search_results)

        if not tracks:
            self.status.emit(f"No songs were found in Deezer for {escape(query)}")
            return

        return tracks

    def addTrack(self, playlist, track):
        if playlist["id"] == self.__loved_playlist:
            r = self.__request(
                method="favorite_song.add",
                data={"SNG_ID": track["id"]}
            )
        else:
            r = self.__request(
                method="playlist.addSongs",
                data={
                    "playlist_id": playlist["id"],
                    "songs": [[track["id"], 0]],
                    "offset": -1
                }
            )

        if not r or "error" in r.json() and r.json()["error"]:
            self.status.emit(f"Failed to add {escape(track['artist'])} - {escape(track['title'])} to {escape(playlist['name'])} playlist in {escape(self.__name)}")
            if r is not None:
                self.log.emit(escape(r.text))
            return False

        return True
