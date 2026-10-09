from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication
import sys

import gui

app = QApplication(sys.argv)

QCoreApplication.setOrganizationName("muSync")
QCoreApplication.setOrganizationDomain("musync.link")
QCoreApplication.setApplicationName("muSync")
QCoreApplication.setApplicationVersion("0.8.0")

mainWindow = gui.MainWindow()

sys.exit(app.exec())
