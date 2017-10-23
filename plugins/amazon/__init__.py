from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QDialog, QLineEdit, QDialogButtonBox, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from urllib.parse import urlparse
import requests, plugins, json

# Sorry for the mess...

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

class Plugin(plugins.Plugin):
    __name = "Amazon Music"
    __authenticated = False
    __cookies = {}
    __amzn = {}
    __webdriver = None

    __login_url = "https://www.amazon.com/gp/dmusic/cloudplayer/forceSignIn/"
    __domain = "music.amazon.com"
    # TODO: Using Chromedriver for debugging, will be replaced by PhantomJS
    __chromedriver_path = "/usr/lib/chromium-browser/chromedriver"

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
        errorMsg = QMessageBox(QMessageBox.Critical, "%s plugin failed" % self.__name, "%s\nTheir site may have changed and this plugin may be outdated. Please check for updates." % message, QMessageBox.Ok, window)
        errorMsg.setModal(True)
        errorMsg.show()

    def __request(self, endpoint, target, data={}, headers={}, redirected=False):
        if not (
            self.__authenticated and
            type(self.__cookies) is dict and
            type(self.__amzn)    is dict and
            "atCookieName"   in self.__amzn and
            "ubidCookieName" in self.__amzn and
            "csrf_rnd"       in self.__amzn and
            "csrf_token"     in self.__amzn and
            "csrf_ts"        in self.__amzn and
            "deviceType"     in self.__amzn and
            "deviceId"       in self.__amzn and
            "customerId"     in self.__amzn and
            self.__amzn["atCookieName"]   in self.__cookies and
            self.__amzn["ubidCookieName"] in self.__cookies
        ):
            if not self.authenticate(window=None, force=True):
                return None

        headers = {
            'Content-Type': 'application/json',
            'Content-Encoding': 'amz-1.0',
            'X-Amz-Target': target,
            'Cookie': '%s=%s; %s=%s' % (self.__amzn["atCookieName"], self.__cookies[self.__amzn["atCookieName"]], self.__amzn["ubidCookieName"], self.__cookies[self.__amzn["ubidCookieName"]]),
            'csrf-rnd': self.__amzn["csrf_rnd"],
            'csrf-token': self.__amzn["csrf_token"],
            'csrf-ts': self.__amzn["csrf_ts"]
        }

        data = {**data, **{
            "deviceType": self.__amzn["deviceType"],
            "deviceId": self.__amzn["deviceId"],
            "customerId": self.__amzn["customerId"]
        }}

        r = requests.post("https://%s/%s" % (self.__domain, endpoint), headers=headers, json=data)

        if (r.status_code == 401):
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
            self.__webdriver.quit()
            self.__webdriver = None
            authDialog.reject()
            return None

        self.__amzn = {
            'deviceId'  :     self.__webdriver.execute_script("return amznMusic.appConfig.deviceId;"),
            'customerId':     self.__webdriver.execute_script("return amznMusic.appConfig.customerId;"),
            'deviceType':     self.__webdriver.execute_script("return amznMusic.appConfig.deviceType;"),
            'csrf_rnd'  :     self.__webdriver.execute_script("return amznMusic.appConfig.CSRFTokenConfig.csrf_rnd;"),
            'csrf_ts'   :     self.__webdriver.execute_script("return amznMusic.appConfig.CSRFTokenConfig.csrf_ts;"),
            'csrf_token':     self.__webdriver.execute_script("return amznMusic.appConfig.CSRFTokenConfig.csrf_token;"),
            'atCookieName':   self.__webdriver.execute_script("return amznMusic.appConfig.atCookieName;"),
            'ubidCookieName': self.__webdriver.execute_script("return amznMusic.appConfig.ubidCookieName;")
        }

        self.__cookies = {}
        for cookie in self.__webdriver.get_cookies():
            self.__cookies[cookie["name"]] = cookie["value"]

        music_url = urlparse(self.__webdriver.current_url)
        self.__domain = music_url.hostname

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
        self.__webdriver.quit()
        self.__webdriver = None

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