from PySide2.QtWidgets import QApplication, QMessageBox
from PySide2.QtGui import QDesktopServices
from PySide2.QtCore import QUrl, QCoreApplication
from os import environ, pathsep
import gui, sys

from selenium import webdriver
from selenium.common.exceptions import WebDriverException

app = QApplication(sys.argv)

QCoreApplication.setOrganizationName("muSync");
QCoreApplication.setOrganizationDomain("musync.link");
QCoreApplication.setApplicationName("muSync");
QCoreApplication.setApplicationVersion("0.5.0");

try:
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("headless")
    chrometest = webdriver.Chrome(executable_path="chromedriver", options=chrome_options)
    chrometest.quit()
    mainWindow = gui.MainWindow()

    sys.exit(app.exec_())
except WebDriverException as e:
    if "executable needs to be in PATH" in e.msg:
        d = QMessageBox(QMessageBox.Critical, "Chromedriver not found",
"""Chromedriver was not found in the path.

Please download Chromedriver from the following address and unzip it in any directory in the system PATH:

https://sites.google.com/a/chromium.org/chromedriver/downloads

Do you want to open this address in your browser?

Current PATH:

{}""".format(environ["PATH"].replace(pathsep, "\n")),
                    QMessageBox.Yes | QMessageBox.No)
        if d.exec() == QMessageBox.Yes:
            QDesktopServices.openUrl(QUrl("https://sites.google.com/a/chromium.org/chromedriver/downloads", QUrl.StrictMode))
        d=QMessageBox(QMessageBox.Information, "Chromedriver not found",
                    "Please restart this application after downloading Chromedriver",
                    QMessageBox.Ok)
        d.exec()
