from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QIcon
import os
import sys

import gui

app = QApplication(sys.argv)
app.setWindowIcon(QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "icon.ico")))

QCoreApplication.setOrganizationName("muSync")
QCoreApplication.setOrganizationDomain("musync.link")
QCoreApplication.setApplicationName("muSync")
QCoreApplication.setApplicationVersion("0.8.0")

gui.MainWindow()

sys.exit(app.exec())
