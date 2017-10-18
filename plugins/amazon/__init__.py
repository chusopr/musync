from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QDialog, QLineEdit, QDialogButtonBox, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, WebDriverException
import requests, plugins

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

    __login_url = "https://www.amazon.com/gp/dmusic/cloudplayer/forceSignIn/"
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

    def __submit_login(self, driver, username, password, waitMsg, authDialog, redirected=False):
        userInput = driver.find_element_by_id('ap_email')
        passInput = driver.find_element_by_id('ap_password')
        if not userInput or not passInput:
            self.__possibly_outdated("Username and/or password input boxes not found in %s site." % self.__name, authDialog)
            waitMsg.close()
            authDialog.reject()
            driver.quit()
            return
        userInput.clear()
        passInput.clear()
        userInput.send_keys(username)
        passInput.send_keys(password)

        captcha = False
        try:
            captcha = driver.find_element_by_id('image-captcha-section')
        except NoSuchElementException:
            pass

        if captcha:
            captcha_img = captcha.find_element_by_tag_name("img")
            captchaForm = CaptchaForm(captcha_img.get_attribute("src"))
            captchaForm.exec()
            if not captchaForm.get_response():
                return False
            captcha_input = driver.find_element_by_name("guess")
            captcha_input.clear()
            captcha_input.send_keys(captchaForm.get_response())
            # A CAPTCHA resets the redirect detector
            redirected = False

        passInput.submit()

        try:
            driver.find_element_by_id('auth-error-message-box')
            # TODO return error message by Amazon
            errorMsg = QMessageBox(QMessageBox.Warning, "Invalid credentials", "The provided credentials%s are not valid for %s.\nPlease make sure the provided e-mail address and password are correct." % (" or text for the CAPTCHA image" if captcha else "", self.__name), QMessageBox.Ok, authDialog)
            errorMsg.setModal(True)
            errorMsg.show()
            waitMsg.close()
            driver.quit()
            return
        except NoSuchElementException:
            pass

        # We only test for a redirect once
        if not redirected:
            redirect_found = False
            try:
                driver.find_element_by_id('ap_email')
                driver.find_element_by_id('ap_password')
                redirect_found = True
            except NoSuchElementException:
                pass

            if redirect_found:
                return self.__submit_login(driver, username, password, waitMsg, authDialog, redirected=True)

    def __login(self, authDialog, username, password):
        waitMsg = QMessageBox(QMessageBox.Information, "Authenticating...", "Please wait while you are being authenticated with %s." % self.__name, QMessageBox.NoButton, authDialog)
        waitMsg.setModal(True)
        waitMsg.show()
        driver = webdriver.Chrome(executable_path=self.__chromedriver_path)
        driver.get(self.__login_url)
        self.__submit_login(driver, username, password, waitMsg, authDialog)

        amznExists = False
        try:
            if driver.execute_script("return amznMusic.appConfig.customerId;"):
                amznExists = True
        except WebDriverException:
            pass

        if not amznExists:
            self.__possibly_outdated("It was not possible to authenticate to %s." % self.__name, authDialog)
            # Should we allow the user to try again with different credentials?
            waitMsg.close()
            driver.quit()
            authDialog.reject()
            return

        amzn = {
            'deviceId'  : driver.execute_script("return amznMusic.appConfig.deviceId;"),
            'customerId': driver.execute_script("return amznMusic.appConfig.customerId;"),
            'deviceType': driver.execute_script("return amznMusic.appConfig.deviceType;"),
            'csrf_rnd'  : driver.execute_script("return amznMusic.appConfig.CSRFTokenConfig.csrf_rnd;"),
            'csrf_ts'   : driver.execute_script("return amznMusic.appConfig.CSRFTokenConfig.csrf_ts;"),
            'csrf_token': driver.execute_script("return amznMusic.appConfig.CSRFTokenConfig.csrf_token;")
        }

        cookies = {}
        for cookie in driver.get_cookies():
            cookies[cookie["name"]] = cookie["value"]

        driver.quit()

        # FIXME: at-acbuk, ubid-acbuk
        headers = {
            'Content-Type': 'application/json',
            'Content-Encoding': 'amz-1.0',
            'X-Amz-Target': 'com.amazon.cirrus.libraryservice.v3.CirrusLibraryServiceExternalV3.reportClientActions',
            'Cookie': 'session-id-time=%s; session-id=%s; at-acbuk=%s; ubid-acbuk=%s' % (cookies["session-id-time"], cookies["session-id"], cookies["at-acbuk"], cookies["ubid-acbuk"]),
            'csrf-rnd': amzn["csrf_rnd"],
            'csrf-token': amzn["csrf_token"],
            'csrf-ts': amzn["csrf_ts"]
        }

        data = {
            "clientActionList": [],
            "deviceType": amzn["deviceType"],
            "deviceId": amzn["deviceId"],
            "customerId": amzn["customerId"]
        }

        api_check = requests.post("https://music.amazon.co.uk/cirrus/v3/", headers=headers, json=data)

        if not api_check.status_code == 200:
            self.__possibly_outdated("Test request to %s failed." % self.__name, authDialog)
            waitMsg.close()
            authDialog.reject()
            return

        self.__authenticated = True
        waitMsg.close()
        authDialog.accept()

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
        buttonBox.rejected.connect(authDialog.reject)
        authDialog.exec()

    def getPlaylists(self):
        return ['My Music']