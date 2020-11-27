from PySide2.QtWidgets import QApplication
import gui, sys

app = QApplication(sys.argv)
mainWindow = gui.MainWindow()

sys.exit(app.exec_())
