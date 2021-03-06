from urllib.parse import urlparse
import modules
import json
import re
import os


class amzn_object_exists(object):
    def __call__(self, driver):
        return driver.execute_script('return typeof amznMusic !== "undefined" && "appConfig" in amznMusic && "customerId" in amznMusic.appConfig;')


class SourceModule(modules.SourceModule):
    __id = "amazon"
    __name = "Amazon Music"
    __read_only = True
    __cookies = {}
    __amzn = {}
    __webdriver = None
    __session = None

    __login_url = "https://www.amazon.com/gp/dmusic/cloudplayer/forceSignIn/"
    __domain = "music.amazon.com"

    def initialize(self):
        self.__session = modules.requests.Session()
        if (self.__id != "amazon"):
            try:
                self.__name = "Amazon Music account {}".format(re.sub(r"amazon-", "", self.__id))
                self.__domain = self.settings().value("{}/domain".format(self.__id))
                if modules.keyring.get_keyring().name == "Windows WinVaultKeyring":
                    # Windows only supports saving credentials up to 512 bytes length
                    i = 0
                    cred = ""
                    cred_chunk = modules.keyring.get_password("muSync", "_".join([self.__id, str(i)]))
                    while cred_chunk:
                        cred = "".join([cred, cred_chunk])
                        i = i + 1
                        cred_chunk = modules.keyring.get_password("muSync", "_".join([self.__id, str(i)]))
                    if cred:
                        self.__cookies, self.__amzn = json.loads(cred)
                else:
                    self.__cookies, self.__amzn = json.loads(modules.keyring.get_password("muSync", self.__id))
                modules.requests.utils.add_dict_to_cookiejar(self.__session.cookies, self.__cookies)
                self.__authenticated = True
            except Exception as e:
                print("Need to re-authenticate: {}".format(str(e)))

    def __save_cache(self):
        try:
            self.settings().setValue("{}/domain".format(self.__id), self.__domain)
            self.__cookies = modules.requests.utils.dict_from_cookiejar(self.__session.cookies)
            if modules.keyring.get_keyring().name == "Windows WinVaultKeyring":
                # Windows only supports saving credentials up to 512 bytes length
                cred = json.dumps([self.__cookies, self.__amzn])
                cred_chunk = cred[0:512]
                i = 0
                while cred_chunk:
                    modules.keyring.set_password("muSync", "_".join([self.__id, str(i)]), cred_chunk)
                    i = i + 1
                    cred_chunk = cred[i * 512:(i + 1) * 512]
            else:
                modules.keyring.set_password("muSync", self.__id, json.dumps([self.__cookies, self.__amzn]))
        except Exception as e:
            print("Failed to cache session data: {}".format(str(e)))

    def __possibly_outdated(self, message, window):
        errorMsg = modules.MessageBox(modules.MessageBox.Critical, "%s module failed" % self.__name, "%s\nTheir site may have changed and this module may be outdated. Please check for updates." % message, modules.MessageBox.Ok, window)
        errorMsg.setModal(True)
        errorMsg.show()

    def __request(self, endpoint, target, data={}, headers={}, redirected=False):
        if not (
            self.__authenticated and
            type(self.__cookies) is dict and
            type(self.__amzn)    is dict and
            "csrf_rnd"   in self.__amzn and
            "csrf_token" in self.__amzn and
            "csrf_ts"    in self.__amzn and
            "deviceType" in self.__amzn and
            "deviceId"   in self.__amzn and
            "customerId" in self.__amzn
        ):
            if not self.authenticate(force=True):
                return None

        headers = {
            'Content-Type': 'application/json',
            'Content-Encoding': 'amz-1.0',
            'X-Amz-Target': target,
            'csrf-rnd': self.__amzn["csrf_rnd"],
            'csrf-token': self.__amzn["csrf_token"],
            'csrf-ts': self.__amzn["csrf_ts"]
        }

        data = {**data, **{
            "deviceType": self.__amzn["deviceType"],
            "deviceId": self.__amzn["deviceId"],
            "customerId": self.__amzn["customerId"]
        }}

        r = self.__session.post("https://%s/%s" % (self.__domain, endpoint), headers=headers, json=data)

        if r.status_code == 401 or r.status_code == 400:
            self.__authenticated = False
            return self.__request(endpoint, target, data, headers, True)

        return r

    def __track_metadata(self, d):
        track = {}
        track["disc"]     = d["discNum"]      if "discNum"      in d else ""
        track["track"]    = d["trackNum"]     if "trackNum"     in d else ""
        track["artist"]   = d["artistName"]   if "artistName"   in d and d["artistName"] != "Unknown Artist" else ""
        track["title"]    = d["title"]        if "title"        in d else ""
        track["duration"] = d["duration"]     if "duration"     in d else ""
        track["album"]    = d["albumName"]    if "albumName"    in d and d["albumName"] != "Unknown Album" else ""
        track["genre"]    = d["primaryGenre"] if "primaryGenre" in d and d["primaryGenre"] != "Unknown Genre" else ""
        return track

    def authenticate(self, force=False):
        if self.__authenticated and not force:
            return True

        if self.__webdriver is None:
            self.__webdriver = modules.WebDriver()
        self.__webdriver.get(self.__login_url)

        if not self.__webdriver.wait(amzn_object_exists):
            self.__webdriver.quit()
            self.__webdriver = None
            self.__authenticated = False
            return False

        self.__amzn = {
            'deviceId':       self.__webdriver.execute_script("return amznMusic.appConfig.deviceId;"),
            'customerId':     self.__webdriver.execute_script("return amznMusic.appConfig.customerId;"),
            'deviceType':     self.__webdriver.execute_script("return amznMusic.appConfig.deviceType;"),
            'csrf_rnd':       self.__webdriver.execute_script("return amznMusic.appConfig.csrf.rnd;"),
            'csrf_ts':        self.__webdriver.execute_script("return amznMusic.appConfig.csrf.ts;"),
            'csrf_token':     self.__webdriver.execute_script("return amznMusic.appConfig.csrf.token;"),
            'atCookieName':   self.__webdriver.execute_script("return amznMusic.appConfig.atCookieName;"),
            'ubidCookieName': self.__webdriver.execute_script("return amznMusic.appConfig.ubidCookieName;")
        }

        self.__cookies = {}
        for cookie in self.__webdriver.get_cookies():
            self.__cookies[cookie["name"]] = cookie["value"]
        modules.requests.utils.add_dict_to_cookiejar(self.__session.cookies, self.__cookies)

        music_url = urlparse(self.__webdriver.current_url)
        self.__domain = music_url.hostname

        self.__id = "amazon-{}".format(self.__amzn["customerId"])
        # Not great, but Amazon Music doesn't really provide a friendly user name
        self.__name = "Amazon Music account {}".format(self.__amzn["customerId"])

        self.__save_cache()

        if self.__webdriver is not None:
            self.__webdriver.quit()
            self.__webdriver = None
        self.__authenticated = True

        api_check = self.__request("cirrus/v3/", "com.amazon.cirrus.libraryservice.v3.CirrusLibraryServiceExternalV3.reportClientActions", data={"clientActionList": []})

        if not api_check or not api_check.status_code == 200:
            self.__possibly_outdated("Test request to %s failed." % self.__name, None)
            self.__authenticated = False
            return False
        return True

    def getPlaylists(self):
        playlists_request = self.__request("cloudplayer/playlists/", "com.amazon.musicplaylist.model.MusicPlaylistService.getOwnedPlaylistsInLibrary")
        amznPlaylists = json.loads(playlists_request.text)

        # Add history playlist
        playlists = [{"id": "my-music", "name": "My music", "writable": False}]
        for p in amznPlaylists["playlists"]:
            playlist = {
                "id": p["playlistId"],
                "name": p["title"],
                "writable": False
            }
            playlists.append(playlist)

        return playlists

    def getTracks(self, playlist):
        tracks = []
        if playlist == 'my-music':
            nextResultsToken = 0
            while nextResultsToken is not None:
                self.status.emit("Please wait while the list of songs is being downloaded ({} donwloaded).".format(nextResultsToken))
                data = {
                    'maxResults': '100',
                    'nextResultsToken': nextResultsToken,
                    'Operation': 'selectTrackMetadata',
                    'selectedColumns.member.1': 'albumArtistName',
                    'selectedColumns.member.2': 'albumName',
                    'selectedColumns.member.3': 'albumReleaseDate',
                    'selectedColumns.member.4': 'artistName',
                    'selectedColumns.member.5': 'duration',
                    'selectedColumns.member.6': 'name',
                    'selectedColumns.member.7': 'sortAlbumArtistName',
                    'selectedColumns.member.8': 'sortAlbumName',
                    'selectedColumns.member.9': 'sortArtistName',
                    'selectedColumns.member.10': 'sortTitle',
                    'selectedColumns.member.1': 'title',
                    'selectCriteriaList.member.1.attributeName': 'status',
                    'selectCriteriaList.member.1.comparisonType': 'EQUALS',
                    'selectCriteriaList.member.1.attributeValue': 'AVAILABLE',
                    'ContentType': 'JSON',
                    'customerInfo.customerId': self.__amzn["customerId"],
                    'customerInfo.deviceId': self.__amzn["deviceId"],
                    'customerInfo.deviceType': self.__amzn["deviceType"]
                }
                headers = {
                    'csrf-rnd': self.__amzn["csrf_rnd"],
                    'csrf-token': self.__amzn["csrf_token"],
                    'csrf-ts': self.__amzn["csrf_ts"]
                }
                tracks_request = self.__session.post("https://{}/cirrus/".format(self.__domain), data=data, headers=headers)

                if tracks_request.status_code != 200:
                    return False
                playlist = json.loads(tracks_request.text)

                if (
                        "selectTrackMetadataResponse" not in playlist or
                        "selectTrackMetadataResult" not in playlist["selectTrackMetadataResponse"] or
                        "trackInfoList" not in playlist["selectTrackMetadataResponse"]["selectTrackMetadataResult"]
                ):
                    return False

                for t in playlist["selectTrackMetadataResponse"]["selectTrackMetadataResult"]["trackInfoList"]:
                    tracks.append(self.__track_metadata(t["metadata"]))

                if "nextResultsToken" in playlist["selectTrackMetadataResponse"]["selectTrackMetadataResult"]:
                    nextResultsToken = playlist["selectTrackMetadataResponse"]["selectTrackMetadataResult"]["nextResultsToken"]
                else:
                    nextResultsToken = None

            self.status.emit("Finished loading tracks")

        else:
            self.status.emit("Please wait while the list of songs is being downloaded")
            data = {
                "playlistIds": [playlist],
                "requestedMetadata": [
                    "albumArtistName",
                    "albumName",
                    "albumReleaseDate",
                    "artistName",
                    "duration",
                    "sortAlbumArtistName",
                    "sortAlbumName",
                    "sortArtistName",
                    "sortTitle",
                    "title"
                ]
            }
            tracks_request = self.__request("cloudplayer/playlists/", "com.amazon.musicplaylist.model.MusicPlaylistService.getPlaylistsByIdV2", data)

            if tracks_request.status_code != 200:
                return False

            playlist = json.loads(tracks_request.text)

            if not playlist or playlist["errors"] or not playlist["playlists"]:
                return False

            tracklist = playlist["playlists"][0]["tracks"]

            for t in tracklist:
                tracks.append(self.__track_metadata(t["metadata"]["requestedMetadata"]))

            self.status.emit("Finished loading tracks")

        return tracks

    def searchTrack(self, track):
        return False

    def addTrack(self, playlist, track):
        return False
