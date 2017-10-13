from PyQt5.QtWidgets import QVBoxLayout, QGridLayout, QLabel, QDialog, QLineEdit, QDialogButtonBox, QMessageBox
from PyQt5.QtCore import Qt
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
import requests, plugins

# Sorry for the mess...

class Plugin(plugins.Plugin):
    __name = "Amazon Music"
    __authenticated = False

    # FIXME: use global URL
    __login_url = "https://www.amazon.co.uk/gp/dmusic/cloudplayer/forceSignIn/ref=dm_wcp_unrec_ctxt_sign_in"
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

    def __login(self, authDialog, username, password):
        waitMsg = QMessageBox(QMessageBox.Information, "Authenticating...", "Please wait while you are being authenticated with %s." % self.__name, QMessageBox.NoButton, authDialog)
        waitMsg.setModal(True)
        waitMsg.show()
        driver = webdriver.Chrome(executable_path=self.__chromedriver_path)
        driver.get(self.__login_url)
        userInput = driver.find_element_by_id('ap_email')
        passInput = driver.find_element_by_id('ap_password')
        if not userInput or not passInput:
            self.__possibly_outdated("Username and/or password input boxes not found in %s site." % self.__name, authDialog)
            waitMsg.close()
            authDialog.reject()
            driver.quit()
            return
        userInput.send_keys(username)
        passInput.send_keys(password)
        passInput.submit()

        try:
            driver.find_element_by_id('auth-error-message-box')
            errorMsg = QMessageBox(QMessageBox.Warning, "Invalid credentials", "The provided credentials are not valid for %s.\nPlease make sure the provided e-mail address and password are correct." % self.__name, QMessageBox.Ok, authDialog)
            errorMsg.show()
            waitMsg.close()
            driver.quit()
            return
        except NoSuchElementException:
            pass

        # TODO: check if we have been redirected
        if not driver.execute_script("return amznMusic.appConfig.customerId;"):
            __possibly_outdated("It was not possible to authenticate to %s." % self.__name, authDialog)
            # Should we allow the user to try again with different credentials?
            waitMsg.close()
            #driver.quit()
            authDialog.reject()
            return

        # TODO: check if a CAPTCHA is required by searching for image-captcha-section

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
            __possibly_outdated("Test request to %s failed." % self.__name, authDialog)
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