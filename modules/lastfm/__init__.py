from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, WebDriverException, TimeoutException
import requests, modules, json, os, re
from math import ceil
from hashlib import md5

class lastfm_createform_ready(object):
    def __call__(self, driver):
        if driver.current_url == "https://www.last.fm/api/account/create" and driver.find_element_by_id("id_name"):
            return driver.execute_script('return document.getElementById("id_name").form;')
        return False

class lastfm_apitable_ready(object):
    def __call__(self, driver):
        try:
            return driver.find_element_by_class_name("auth-dropdown-menu-item") and driver.find_element_by_class_name("api-details-table")
        except NoSuchElementException:
            return False

class lastfm_authtoken_success:
    def __call__(self, driver):
        try:
            return driver.find_element_by_class_name("alert-success")
        except NoSuchElementException:
            return False


class SourceModule(modules.SourceModule):
    __id = "lastfm"
    __name = "Last.fm"
    # Get your API key from https://www.last.fm/api/account/create
    __api_key = None
    __api_secret = None
    __session_key = None

    __webdriver = None
    __login_url = "https://last.fm/api/account/create"
    __chromedriver_path = "/usr/bin/chromedriver"

    __username = None

    def __save_cache(self):
        try:
            os.makedirs(os.path.dirname(self.__session_file), 0o700, True)
            with open(self.__session_file, "w") as f:
                json.dump([self.__username, self.__api_key, self.__api_secret], f)
        except Exception as e:
            print("Failed to cache session data: {}".format(str(e)))

    def initialize(self):
        if not self.__id == "lastfm":
            self.__set_session_file()
            if (os.path.isfile(self.__session_file)):
                try:
                    with open(self.__session_file, "r") as f:
                        self__username, self.__api_key, self.__api_secret = json.load(f)
                    self.__username = re.sub(r"lastfm-", "", self.__id)
                    self.__name = "{}'s Last.fm account".format(self.__username)
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

    def isAuthenticated(self):
        return self.__authenticated

    def __get_session_key(self):
        if self.__session_key is not None:
            return self.__session_key

        token_request = requests.get("http://ws.audioscrobbler.com/2.0/?method=auth.gettoken&api_key={}&api_sig={}&format=json".format(
            self.__api_key,
            md5("api_key{}methodauth.getToken{}".format(self.__api_key, self.__api_secret).encode("utf-8"))
        ))

        try:
            token_request_json = json.loads(token_request.text)
        except:
            pass

        if token_request.status_code != 200 or "token" not in token_request_json:
            self.status.emit("Error authenticating to Last.fm")
            return False

        auth_token = token_request_json["token"]

        if self.__webdriver == None:
            self.__webdriver = webdriver.Chrome(executable_path=self.__chromedriver_path)
        self.__webdriver.get("http://www.last.fm/api/auth/?api_key={}&token={}".format(self.__api_key, auth_token))

        auth_token_success = False
        while not auth_token_success:
            try:
                wait = webdriver.support.ui.WebDriverWait(self.__webdriver, 3)
                auth_token_success = wait.until(lastfm_authtoken_success())
            except TimeoutException:
                pass
            except WebDriverException as e:
                self.status.emit(e)
                return False

        self.__webdriver.quit()
        self.__webdriver = None

        session_request = requests.get("http://ws.audioscrobbler.com/2.0/?method=auth.getsession&api_key={}&token={}&api_sig={}&format=json".format(
            self.__api_key,
            auth_token,
            md5("api_key{}methodauth.getsessiontoken{}{}".format(self.__api_key, auth_token, self.__api_secret).encode("utf-8")).hexdigest()
        ))

        try:
            session_request_json = json.loads(session_request.text)
        except:
            pass

        if session_request.status_code != 200 or "session" not in session_request_json or "key" not in session_request_json["session"]:
            self.status.emit("Error authenticating to Last.fm")
            return False

        self.__session_key = session_request_json["session"]["key"]

        return self.__session_key

    def authenticate(self, force=False):
        if self.__authenticated and not force:
            return True

        if self.__webdriver == None:
            self.__webdriver = webdriver.Chrome(executable_path=self.__chromedriver_path)
        self.__webdriver.get(self.__login_url)

        create_form = False
        while not create_form:
            try:
                wait = webdriver.support.ui.WebDriverWait(self.__webdriver, 3)
                create_form = wait.until(lastfm_createform_ready())
            except TimeoutException:
                pass
            except WebDriverException as e:
                self.status.emit(e)
                break

        if not create_form:
            self.__webdriver.quit()
            self.__webdriver = None
            self.__authenticated = False
            return False

        name_element = self.__webdriver.find_element_by_id("id_name")

        try:
            homepage_element = self.__webdriver.find_element_by_id("id_homepage")
            if homepage_element:
                homepage_element.send_keys("https://musync.link")
        except:
            pass

        name_element.send_keys("muSync")

        create_form.submit()

        api_details = False
        while not api_details:
            try:
                wait = webdriver.support.ui.WebDriverWait(self.__webdriver, 3)
                api_details = wait.until(lastfm_apitable_ready())
            except TimeoutException:
                pass
            except WebDriverException as e:
                self.status.emit(e)
                break

        self.__username = self.__webdriver.execute_script('return document.getElementsByClassName("auth-dropdown-menu-item")[0].children[0].textContent;')
        self.__api_key = self.__webdriver.execute_script('return document.getElementsByClassName("api-details-table")[0].rows[1].cells[1].textContent;')

        try:
            userinfo_request = requests.get("http://ws.audioscrobbler.com/2.0/?method=user.getinfo&user={}&api_key={}&format=json".format(self.__username, self.__api_key))
            if userinfo_request.status_code != 200:
                return False # do something
            userinfo = json.loads(userinfo_request.text)
        except:
            pass

        if not (userinfo and "user" in userinfo and "name" in userinfo["user"]):
            return False # do something

        self.__name = "{}'s Last.fm account".format(userinfo["user"]["name"])
        self.__id = "lastfm-{}".format(self.__username)

        self.__set_session_file()

        self.__save_cache()

        if self.__webdriver is not None:
            self.__webdriver.quit()
            self.__webdriver = None
        self.__authenticated = True

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
        # Last.fm allows scrobbling or faving tracks that don't exist in their
        # catalog, which will auto-create them, so we always give the choice to
        # add the song with the same verbatim name it has in the other source,
        # unless a verbatim result was already found in their catalog
        verbatim_found = False

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
                    "id":     {"artist": d["artist"], "title": d["name"]}
                })
                # Check if this seach result matches the same exact name as in the other source
                # so we don't need to explicitly add the verbatim result to the returned search results.
                # We make the comparison case insensitive because Last.fm is case insensitive.
                if (track["artist"].lower() == d["artist"].lower() and track["title"].lower() == d["name"].lower()):
                    verbatim_found = True

            total_pages = ceil(float(search_results["results"]["opensearch:totalResults"])/int(search_results["results"]["opensearch:itemsPerPage"]))
            current_page = current_page + 1
            # Get only one page for now
            break

        if not verbatim_found:
            tracks.append({
                "artist": track["artist"],
                "title":  track["title"],
                "id":     {"artist": track["artist"], "title": track["title"]}
            })

        return tracks

    def addTrack(self, playlist, track):
        if playlist["id"] == "loved":
            if not self.__get_session_key():
                return False

            love_request = requests.post("http://ws.audioscrobbler.com/2.0/", data={
                "method": "track.love",
                "track": track["title"],
                "artist": track["artist"],
                "api_key": self.__api_key,
                "sk": self.__session_key,
                "api_sig": md5("api_key{}artist{}methodtrack.lovesk{}track{}{}".format(self.__api_key, track["artist"], self.__session_key, track["title"], self.__api_secret).encode("utf-8")).hexdigest(),
                "format": "json"
            })

            if love_request.status_code == 200:
                return True

            self.log.emit("Failed to add {} - {} to {} playlist in {}: {}".format(track["artist"], track["title"], playlist["name"], self.__name, love_request.text))

        return False
