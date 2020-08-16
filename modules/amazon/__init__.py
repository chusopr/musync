from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QDialog, QLineEdit, QDialogButtonBox, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from urllib.parse import urlparse
import requests, modules, json
from appdirs import user_cache_dir
import os, re

class CaptchaForm(QDialog):
    __captcha_response = None

    def __init__(self, imgurl):
        super().__init__()

        windowLayout = QVBoxLayout(self)

        imageLabel = QLabel(self)
        image_request = requests.get(imgurl)
        captcha_image = QPixmap()
        captcha_image.loadFromData(image_request.content)
        imageLabel.setPixmap(captcha_image)
        windowLayout.addWidget(imageLabel)

        captchaLayout = QHBoxLayout()

        captchaLayout.addWidget(QLabel("Please input the text in the image:"))
        captchaText = QLineEdit(self)
        captchaLayout.addWidget(captchaText)
        windowLayout.addLayout(captchaLayout)

        buttonBox = QDialogButtonBox(self);
        buttonBox.setOrientation(Qt.Horizontal)
        buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok);

        windowLayout.addWidget(buttonBox);

        buttonBox.accepted.connect(lambda: self.__set_response(captchaText.text()))
        buttonBox.rejected.connect(self.reject)

        self.setWindowTitle('CAPTCHA required')

    def __set_response(self, text):
        self.__captcha_response = text
        self.accept()

    def get_response(self):
        return self.__captcha_response

class OtpForm(QDialog):
    __otp_response = None

    def __init__(self, msg):
        super().__init__()

        windowLayout = QVBoxLayout(self)

        if msg != "":
            windowLayout.addWidget(QLabel(msg))

        formLayout = QHBoxLayout()

        formLayout.addWidget(QLabel("Insert one-time password received via text message (SMS) or authenticator app:"))
        otpInput = QLineEdit(self)
        formLayout.addWidget(otpInput)
        windowLayout.addLayout(formLayout)

        buttonBox = QDialogButtonBox(self);
        buttonBox.setOrientation(Qt.Horizontal)
        buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok);

        windowLayout.addWidget(buttonBox);

        buttonBox.accepted.connect(lambda: self.__set_response(otpInput.text()))
        buttonBox.rejected.connect(self.reject)

        self.setWindowTitle('One-time password required')

    def __set_response(self, text):
        self.__otp_response = text
        self.accept()

    def get_response(self):
        return self.__otp_response

class SourceModule(modules.SourceModule):
    __id = "amazon"
    __name = "Amazon Music"
    __authenticated = False
    __cookies = {}
    __amzn = {}
    __webdriver = None
    __session = requests.Session()

    __login_url = "https://www.amazon.com/gp/dmusic/cloudplayer/forceSignIn/"
    __domain = "music.amazon.com"
    # TODO: Using Chromedriver for debugging, will be replaced by PhantomJS
    __chromedriver_path = "/usr/bin/chromedriver"

    def __set_session_file(self):
        self.__session_file = os.path.join(user_cache_dir("musync"), "{}.session".format(self.__id))

    def initialize(self):
        self.__set_session_file()
        self.__name = "Amazon Music account {}".format(re.sub(r"amazon-", "", self.__id))
        if (os.path.isfile(self.__session_file)):
            try:
                with open(self.__session_file, "r") as f:
                    self.__domain, self.__cookies, self.__amzn = json.load(f)
                requests.utils.add_dict_to_cookiejar(self.__session.cookies, self.__cookies)
                self.__authenticated = True

            except Exception as e:
                print("Need to re-authenticate: {}".format(str(e)))

    def __save_cache(self):
        try:
            self.__cookies = requests.utils.dict_from_cookiejar(self.__session.cookies)
            os.makedirs(os.path.dirname(self.__session_file), 0o700, True)
            with open(self.__session_file, "w") as f:
                json.dump([self.__domain, self.__cookies, self.__amzn], f)
        except Exception as e:
            print("Failed to cache session data: {}".format(str(e)))

    def __http_debug(self):
        import http.client as http_client
        import logging
        http_client.HTTPConnection.debuglevel = 1
        logging.basicConfig()
        logging.getLogger().setLevel(logging.DEBUG)
        requests_log = logging.getLogger("requests.packages.urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True

    def __possibly_outdated(self, message, window):
        errorMsg = QMessageBox(QMessageBox.Critical, "%s module failed" % self.__name, "%s\nTheir site may have changed and this module may be outdated. Please check for updates." % message, QMessageBox.Ok, window)
        errorMsg.setModal(True)
        errorMsg.show()

    def __request(self, endpoint, target, data={}, headers={}, redirected=False):
        if not (
            self.__authenticated and
            type(self.__cookies) is dict and
            type(self.__amzn)    is dict and
            "csrf_rnd"       in self.__amzn and
            "csrf_token"     in self.__amzn and
            "csrf_ts"        in self.__amzn and
            "deviceType"     in self.__amzn and
            "deviceId"       in self.__amzn and
            "customerId"     in self.__amzn
        ):
            if not self.authenticate(window=None, force=True):
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

    def __submit_login(self, username, password, redirected=False):
        userInput = self.__webdriver.find_element_by_id('ap_email')
        passInput = self.__webdriver.find_element_by_id('ap_password')
        if not userInput or not passInput:
            self.__possibly_outdated("Username and/or password input boxes not found in %s site." % self.__name, self)
            return None
        userInput.clear()
        passInput.clear()
        userInput.send_keys(username)
        passInput.send_keys(password)

        captcha = False
        try:
            captcha = self.__webdriver.find_element_by_id('image-captcha-section')
        except NoSuchElementException:
            pass

        if captcha:
            captcha_img = captcha.find_element_by_tag_name("img")
            captchaForm = CaptchaForm(captcha_img.get_attribute("src"))
            captchaForm.exec()
            if not captchaForm.get_response():
                return False
            captcha_input = self.__webdriver.find_element_by_name("guess")
            captcha_input.clear()
            captcha_input.send_keys(captchaForm.get_response())
            # A CAPTCHA resets the redirect detector
            redirected = False

        try:
            rememberMe_checkbox = self.__webdriver.find_element_by_name("rememberMe")
            if not rememberMe_checkbox.is_selected():
                rememberMe_checkbox.click()
        except NoSuchElementException:
            pass
        passInput.submit()

        try:
            self.__webdriver.find_element_by_id('auth-error-message-box')
            # TODO return error message by Amazon
            errorMsg = QMessageBox(QMessageBox.Warning, "Invalid credentials", "The provided credentials%s are not valid for %s.\nPlease make sure the provided e-mail address and password are correct." % (" or text for the CAPTCHA image" if captcha else "", self.__name), QMessageBox.Ok)
            errorMsg.setModal(True)
            errorMsg.exec()
            return False
        except NoSuchElementException:
            pass

        otp_error = ""
        try:
            otp = self.__webdriver.find_element_by_id('auth-mfa-otpcode')
        except NoSuchElementException:
            pass

        while otp:
            # Show OTP query form
            otpForm = OtpForm(otp_error)
            otpForm.exec()
            # User aborted? Finish
            if not otpForm.get_response():
                return False
            # Input OTP details
            otp.clear()
            otp.send_keys(otpForm.get_response())
            # Try to check the box to not ask for OTP again
            # Ignore it if it fails
            try:
                otpRemember_checkbox = self.__webdriver.find_element_by_id("auth-mfa-remember-device")
                if not otpRemember_checkbox.is_selected():
                    otpRemember_checkbox.click()
            except NoSuchElementException:
                pass

            # Submit OTP form
            otp.submit()
            # Check if we are asked for the OTP again
            # meaning the provided one is not valid
            otp = False
            try:
                otp = self.__webdriver.find_element_by_id('auth-mfa-otpcode')
            except NoSuchElementException:
                pass
            # If we are asked again for the OTP, try to get the error message
            # to return it to the user
            if otp:
                try:
                    otp_error_box = self.__webdriver.find_element_by_id('auth-error-message-box')
                    otp_error = otp_error_box.find_element_by_tag_name("span").text
                except NoSuchElementException:
                    pass

        # We only test for a redirect once
        if not redirected:
            redirect_found = False
            try:
                self.__webdriver.find_element_by_id('ap_email')
                self.__webdriver.find_element_by_id('ap_password')
                redirect_found = True
            except NoSuchElementException:
                pass

            if redirect_found:
                return self.__submit_login(username, password, redirected=True)

        return True

    def __login(self, authDialog, username, password):
        waitMsg = QMessageBox(QMessageBox.Information, "Authenticating...", "Please wait while you are being authenticated with %s." % self.__name, QMessageBox.NoButton, authDialog)
        waitMsg.setModal(True)
        waitMsg.show()
        if self.__webdriver == None:
            self.__webdriver = webdriver.Chrome(executable_path=self.__chromedriver_path)
        self.__webdriver.get(self.__login_url)
        login_result = self.__submit_login(username, password)

        if login_result == None:
            waitMsg.close()
            if self.__webdriver is not None:
                self.__webdriver.quit()
                self.__webdriver = None
            self.__possibly_outdated("It was not possible to authenticate to %s." % self.__name, authDialog)
            authDialog.reject()
            return login_result
        elif login_result == False:
            waitMsg.close()
            return login_result

        amznExists = False
        try:
            if self.__webdriver.execute_script("return amznMusic.appConfig.customerId;"):
                amznExists = True
        except WebDriverException:
            pass

        if not amznExists:
            # Should we allow the user to try again with different credentials?
            waitMsg.close()
            if self.__webdriver is not None:
                self.__webdriver.quit()
                self.__webdriver = None
            authDialog.reject()
            return None

        self.__amzn = {
            'deviceId'  :     self.__webdriver.execute_script("return amznMusic.appConfig.deviceId;"),
            'customerId':     self.__webdriver.execute_script("return amznMusic.appConfig.customerId;"),
            'deviceType':     self.__webdriver.execute_script("return amznMusic.appConfig.deviceType;"),
            'csrf_rnd'  :     self.__webdriver.execute_script("return amznMusic.appConfig.csrf.rnd;"),
            'csrf_ts'   :     self.__webdriver.execute_script("return amznMusic.appConfig.csrf.ts;"),
            'csrf_token':     self.__webdriver.execute_script("return amznMusic.appConfig.csrf.token;"),
            'atCookieName':   self.__webdriver.execute_script("return amznMusic.appConfig.atCookieName;"),
            'ubidCookieName': self.__webdriver.execute_script("return amznMusic.appConfig.ubidCookieName;")
        }

        self.__cookies = {}
        for cookie in self.__webdriver.get_cookies():
            self.__cookies[cookie["name"]] = cookie["value"]
        requests.utils.add_dict_to_cookiejar(self.__session.cookies, self.__cookies)

        music_url = urlparse(self.__webdriver.current_url)
        self.__domain = music_url.hostname

        self.__id = "amazon-{}".format(self.__amzn["customerId"])
        # Not great, but Amazon Music doesn't really provide a friendly user name
        self.__name = "Amazon Music account {}".format(self.__amzn["customerId"])
        self.__set_session_file()

        self.__save_cache()

        if self.__webdriver is not None:
            self.__webdriver.quit()
            self.__webdriver = None
        self.__authenticated = True

        api_check = self.__request("cirrus/v3/", "com.amazon.cirrus.libraryservice.v3.CirrusLibraryServiceExternalV3.reportClientActions", data={"clientActionList": []})

        if not api_check or not api_check.status_code == 200:
            self.__possibly_outdated("Test request to %s failed." % self.__name, None)
            self.__authenticated = False
            waitMsg.close()
            authDialog.reject()
            return None

        waitMsg.close()
        authDialog.accept()

    def __reject_auth(self, authDialog):
        authDialog.reject()
        if self.__webdriver is not None:
            self.__webdriver.quit()
            self.__webdriver = None

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

    def authenticate(self, window, force=False):
        if self.__authenticated and not force:
            return True
        authDialog = QDialog(window)
        authLayout = QVBoxLayout(authDialog)

        authLabel = QLabel("Please authenticate with your %s account" % self.__name, authDialog)

        authLayout.addWidget(authLabel)

        userpassLayout = QGridLayout()

        userpassLayout.addWidget(QLabel("E-mail:", authDialog), 0, 0)
        userInput = QLineEdit(authDialog)
        userpassLayout.addWidget(userInput, 0, 1)

        userpassLayout.addWidget(QLabel("Password:", authDialog), 1, 0)
        passInput = QLineEdit(authDialog)
        passInput.setEchoMode(QLineEdit.Password)
        userpassLayout.addWidget(passInput, 1, 1)

        authLayout.addLayout(userpassLayout)

        buttonBox = QDialogButtonBox(authDialog);
        buttonBox.setOrientation(Qt.Horizontal)
        buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok);

        authLayout.addWidget(buttonBox);

        buttonBox.accepted.connect(lambda: self.__login(authDialog, userInput.text(), passInput.text()))
        buttonBox.rejected.connect(lambda: self.__reject_auth(authDialog))
        return True if authDialog.exec() == QDialog.Accepted else False

    def getPlaylists(self):
        playlists_request = self.__request("cloudplayer/playlists/", "com.amazon.musicplaylist.model.MusicPlaylistService.getOwnedPlaylistsInLibrary")
        amznPlaylists = json.loads(playlists_request.text)

        # Add history playlist
        playlists = [{"id": "my-music", "name": "My music", "writable": True}]
        for p in amznPlaylists["playlists"]:
            playlist = {
                "id": p["playlistId"],
                "name": p["title"],
                "writable": p["canEditContents"]
            }
            playlists.append(playlist)

        return playlists

    def getTracks(self, playlist):
        tracks = []
        if playlist == 'my-music':
            nextResultsToken = 0
            while nextResultsToken is not None:
                self.__main.statusBar().showMessage("Please wait while the list of songs is being downloaded ({} donwloaded).".format(nextResultsToken))
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
                tracks_request = self.__session.post("https://music.amazon.co.uk/cirrus/", data=data, headers=headers)

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

            self.__main.statusBar().showMessage("Finished loading tracks")

        else:
            self.__main.statusBar().showMessage("Please wait while the list of songs is being downloaded")
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

            self.__main.statusBar().showMessage("Finished loading tracks")

        return tracks

    def deleteAccount(self):
        if (os.path.isfile(self.__session_file)):
            os.remove(self.__session_file)
