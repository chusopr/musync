from dialogs.browser import Browser
import ytmusicapi
import json
import re
from html import escape
from ytmusicapi.models.content.enums import LikeStatus

import modules


class SourceModule(modules.SourceModule):
    __id = "ytmusic"
    __name = "YouTube Music"
    __login_url = "https://www.youtube.com/signin?next=https%3A%2F%2Fmusic.youtube.com%2F"

    def __save_cache(self):
        try:
            modules.keyring.set_password("muSync", self.__id, json.dumps([self.__authorization, self.__cookies]))
        except Exception as e:
            print("Failed to cache session data: {}".format(str(e)))

    def __setup_ytm(self):
        ytm_auth = ytmusicapi.setup(headers_raw="\n".join([
            f"Authorization: {self.__authorization}",
            f"Cookie: {self.__cookies}",
            "Accept: */*",
            "Content-Type: application/json",
            "X-Goog-AuthUser: 0",
            "x-origin: https://music.youtube.com"
        ]))
        self.__ytm = ytmusicapi.YTMusic(auth=ytm_auth)
        return self.__ytm.get_account_info()

    def initialize(self):
        self.__cookies = ""
        self.__authorization = ""
        if not self.__id == "ytmusic":
            try:
                self.__username = re.sub(r"ytmusic-", "", self.__id)
                self.__name = f"{self.__username}'s YouTube Music account"
                self.__authorization, self.__cookies = json.loads(modules.keyring.get_password("muSync", self.__id))
                self.__setup_ytm()
                self.__authenticated = True
            except Exception as e:
                print("Need to re-authenticate: {}".format(str(e)))

    def isAuthenticated(self):
        return self.__authenticated

    def authenticate(self, force=False, parent=None):
        if not self.__authenticated or force:
            browser = Browser(parent)
            browser.get(self.__login_url)
            browser.show()
            auth_found = False
            while not auth_found:
                request = browser.intercept_request("POST")
                if request is None:
                    self.status.emit("Authentication to YouTube Music cancelled")
                    browser.deleteLater()
                    return False
                if "headers" in request and "Authorization" in request["headers"]:
                    self.__authorization = request["headers"]["Authorization"]
                    cookies = []
                    for d, c in browser.get_cookies().items():
                        if d in (".youtube.com", "music.youtube.com"):
                            for n, v in c.items():
                                cookies.append(f"{n}={v['value']}")
                    self.__cookies = "; ".join(cookies)
                    auth_found = True
                    browser.accept()
            browser.deleteLater()
            try:
                userinfo = self.__setup_ytm()
            except Exception as e:
                self.status.emit("Error getting YouTube user details")
                self.log.emit(escape(str(e)))
                return False

            if "channelHandle" not in userinfo:
                self.status.emit("Error getting YouTube user details")
                self.log.emit(escape("User doesn't have a handle"))
                return False

            self.__username = userinfo['channelHandle'][1:]
            self.__name = f"{self.__username}'s YouTube Music account"
            self.__id = f"ytmusic-{self.__username}"

            self.__authenticated = True

        self.__save_cache()

        return True

    def getPlaylists(self):
        if self.__authenticated:
            self.__playlists = {}
            for p in self.__ytm.get_library_playlists():
                self.__playlists[p["playlistId"]] = {
                    "name": p["title"],
                    # Liked Music and Episodes for Later are not owned by us
                    # but we can write to them
                    # TODO we can also write to playlists where we are a
                    # contributor even if not owned by us
                    "writable": p["owned"] or p["playlistId"] == "LM" or p["playlistId"] == "SE"
                }
            return [{"id": k, "name": v["name"], "writable": v["writable"]} for k, v in self.__playlists.items()]

    def __track_metadata(self, t):
        track = {}

        artist = ""
        if "artist" in t:
            artist = t["artist"]
        elif "artists" in t:
            artist = ", ".join([artists['name'] for artists in t["artists"]])

        track["artist"] = artist
        track["title"] = t["title"] if "title" in t else ""

        return track

    def getTracks(self, playlist_id, cancel):
        tracks = []
        playlist = {}
        playlist_name = self.__playlists[playlist_id]["name"] if playlist_id in self.__playlists else playlist_id
        try:
            playlist = self.__ytm.get_playlist(playlist_id, limit=None, related=False, suggestions_limit=0)
        except Exception as e:
            self.status.emit(f"Failed loading playlist {playlist_name} in YouTube Music account {self.__username}")
            self.log.emit(escape(str(e)))
            return

        if "tracks" not in playlist:
            return None

        for t in playlist["tracks"]:
            tracks.append(self.__track_metadata(t))

        if cancel.is_set():
            self.log.emit(f"Loading tracks for {playlist_name} playlist in YouTube Music account {self.__username} was cancelled")
            return

        self.status.emit("Finished loading tracks")
        return tracks

    def searchTrack(self, track):
        search_string = ""
        if "search_artist" in track:
            search_string = f"{track['search_artist']} "
        elif "artist" in track:
            search_string = f"{track['artist']} "
        if "search_title" in track:
            search_string += track["search_title"]
        elif "title" in track:
            search_string += track["title"]

        if not search_string.strip():
            return

        tracks = []
        try:
            results = self.__ytm.search(search_string, filter="songs")
        except Exception as e:
            self.status.emit(f"Failed searching song {search_string} in YouTube Music")
            self.log.emit(escape(str(e)))
            return

        for r in results:
            track = self.__track_metadata(r)
            track["id"] = r["videoId"]
            tracks.append(track)

        return tracks

    def addTrack(self, playlist, track):
        track_name = f"{track['artist']} - " if "artist" in track else ""
        track_name += track["title"]

        if "id" not in track:
            self.status.emit(f"Cannot add track {track_name} to {playlist['name']} in YouTube Music account {self.__username}")
            self.log.emit("The track doesn't have a video ID")
            return False

        try:
            if playlist["id"] == "LM":
                # You cannot add a song to the liked playlist directly
                # instead, you rate it as liked
                results = self.__ytm.rate_song(track["id"], LikeStatus.LIKE)
            else:
                results = self.__ytm.add_playlist_items(playlist["id"], [track["id"]])
                if "status" in results and results["status"] == "STATUS_SUCCEEDED":
                    return True
                return False
        except Exception as e:
            self.status.emit(f"Cannot add track {track_name} to {playlist['name']} in YouTube Music account {self.__username}")
            self.log.emit(escape(str(e)))
            return False

        return True
