from PyQt5.QtWidgets import QMainWindow, QWidget, QAction, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QMenuBar, QLabel, QComboBox, QDialog, QMessageBox, QListWidgetItem
from PyQt5.QtCore import QCoreApplication, Qt
from PyQt5.QtGui import QIcon
import re, plugins

class MainWindow(QMainWindow):
    sources = {
        "left":  None,
        "right": None
    }

    def __init__(self):
        super().__init__()
        self.buildUI()

    def bogus_plugin(self, plugin_name):
        errorMsg = QMessageBox(QMessageBox.Critical, "Bogus plugin", plugin_name + " plugin is not working properly", QMessageBox.Ok, self)
        errorMsg.show()

    def change_source(window, source_name, sourceDialog, sourcesList, sourceName):
        plugin_name = sourcesList.currentItem().text()
        plugin_slug = sourcesList.currentItem().slug
        if not plugin_slug in plugins.plugins:
            window.bogus_plugin(plugin_name)
            return
        source = plugins.plugins[plugin_slug]
        if not "getTracklists" in dir(source):
            window.bogus_plugin(plugin_name)
            return
        playlists = source.getTracklists()
        if not playlists or len(playlists) == 0:
            window.bogus_plugin(plugin_name)
            return
        window.findChild(QLabel, sourceName + "SourceLabel").setText("Selected source: " + plugin_name)
        window.sources[sourceName] = plugin_slug
        playlistSelect = window.findChild(QComboBox, source_name + "Playlist")
        for playlist in playlists:
            playlistSelect.addItem(playlist)
        sourceDialog.close()

    def source_select(self, source_name):
        sources = plugins.listAll()
        if len(sources) == 0:
            errorMsg = QMessageBox(QMessageBox.Critical, "No sources available", "No source plugins found", QMessageBox.Ok, self)
            errorMsg.show()
            return
        sourceName = re.sub(r"SourceBtn$", "", self.sender().objectName())
        sourceDialog = QDialog(self)
        sourceDialog.setModal(True)
        dialogLayout = QVBoxLayout(sourceDialog)
        sourcesList = QListWidget()
        dialogLayout.addWidget(sourcesList)
        buttonsLayout = QHBoxLayout()
        okButton = QPushButton(QIcon.fromTheme("dialog-ok"), "&Ok")
        okButton.clicked.connect(lambda: self.change_source(source_name, sourceDialog, sourcesList, sourceName))
        buttonsLayout.addWidget(okButton)
        cancelButton = QPushButton(QIcon.fromTheme("dialog-cancel"), "&Cancel")
        cancelButton.clicked.connect(sourceDialog.close)
        buttonsLayout.addWidget(cancelButton)
        dialogLayout.addLayout(buttonsLayout)
        for source in sources.items():
            sourceItem = QListWidgetItem(source[1])
            sourceItem.slug = source[0]
            sourcesList.addItem(sourceItem)
        sourcesList.itemDoubleClicked.connect(lambda: self.change_source(source_name, sourceDialog, sourcesList, sourceName))
        sourceDialog.show()

    def create_source_layout(self, source_name):
        sourceLayout = QVBoxLayout()
        selectedSourceLayout = QHBoxLayout()
        sourceLabel = QLabel("Selected source: None")
        sourceLabel.setObjectName(source_name + "SourceLabel")
        selectedSourceLayout.addWidget(sourceLabel, 1)
        changeSourceBtn = QPushButton("Change...")
        changeSourceBtn.setObjectName(source_name + "SourceBtn")
        changeSourceBtn.clicked.connect(lambda: self.source_select(source_name))
        selectedSourceLayout.addWidget(changeSourceBtn)
        playlistLabel = QLabel("Selected playlist:")
        selectedSourceLayout.addWidget(playlistLabel)
        playlistSelect = QComboBox()
        playlistSelect.setObjectName(source_name + "Playlist")
        selectedSourceLayout.addWidget(playlistSelect, 1)
        sourceLayout.addLayout(selectedSourceLayout)

        trackList = QListWidget()
        trackList.setObjectName(source_name + "Tracklist")
        sourceLayout.addWidget(trackList)
        return (sourceLayout, playlistSelect, trackList, changeSourceBtn)

    def start_sync(self):
        if not (self.sources["left"] and self.sources["right"] and self.playlists["left"] and self.playlists["right"]):
            errorMsg = QMessageBox(QMessageBox.Warning, "No sources selected", "You must select sources and playlists first", QMessageBox.Ok, self)
            errorMsg.show()
            return
        errorMsg = QMessageBox(QMessageBox.Warning, "No sources selected", "OK first", QMessageBox.Ok, self)
        errorMsg.show()

    def buildUI(self):
        centralWidget = QWidget(self)
        windowLayout = QVBoxLayout(centralWidget)

        mainLayout = QHBoxLayout()

        leftLayout, leftPlaylist, leftTracklist, leftSourceBtn = self.create_source_layout("left")
        mainLayout.addLayout(leftLayout)
        rightLayout, rightPlaylist, rightTracklist, rightSourceBtn = self.create_source_layout("right")
        mainLayout.addLayout(rightLayout)

        windowLayout.addLayout(mainLayout)

        buttonsWidget = QWidget()
        buttonsLayout = QHBoxLayout(buttonsWidget)
        syncBtn = QPushButton(QIcon.fromTheme("system-run"), "S&ync")
        syncBtn.clicked.connect(self.start_sync)
        buttonsLayout.addWidget(syncBtn, 1, Qt.AlignRight)
        settingsBtn = QPushButton(QIcon.fromTheme("preferences-other"), "&Settings")
        buttonsLayout.addWidget(settingsBtn, 1, Qt.AlignRight)
        exitBtn = QPushButton(QIcon.fromTheme("window-close"), "Quit")
        exitBtn.clicked.connect(QCoreApplication.instance().quit)
        buttonsLayout.addWidget(exitBtn, 1, Qt.AlignRight)
        windowLayout.addWidget(buttonsWidget, 1, Qt.AlignRight)

        # Build menu bar
        mainMenu = QMenuBar(self)
        fileMenu = mainMenu.addMenu("&File")
        syncMenuItem = QAction(QIcon.fromTheme("system-run"), "Start s&yncing", fileMenu)
        syncMenuItem.setShortcut("Ctrl+S")
        fileMenu.addAction(syncMenuItem)
        settingsMenuItem = QAction(QIcon.fromTheme("preferences-other"), "&Settings", fileMenu)
        settingsMenuItem.setShortcut("Ctrl+P")
        fileMenu.addAction(settingsMenuItem)
        fileMenu.addAction(fileMenu.addSeparator())
        exitMenuItem = QAction(QIcon.fromTheme("window-close"), "&Exit", fileMenu)
        exitMenuItem.setShortcut("Ctrl+Q")
        exitMenuItem.triggered.connect(QCoreApplication.instance().quit)
        fileMenu.addAction(exitMenuItem)
        viewMenu = mainMenu.addMenu("&View")
        logMenuItem = QAction(QIcon.fromTheme("text-x-generic"), "&Logs", viewMenu)
        logMenuItem.setShortcut("Ctrl+L")
        viewMenu.addAction(logMenuItem)
        self.setMenuBar(mainMenu);

        # Set tab order
        # It doesn't work :-(
        #QWidget.setTabOrder(syncBtn, settingsBtn)
        #QWidget.setTabOrder(settingsBtn, exitBtn)
        #QWidget.setTabOrder(exitBtn, leftSourceBtn)
        #QWidget.setTabOrder(leftSourceBtn, rightSourceBtn)
        #QWidget.setTabOrder(rightSourceBtn, leftTracklist)
        #QWidget.setTabOrder(leftList, rightTracklist)

        syncBtn.setFocus(Qt.OtherFocusReason)

        # Show window
        self.setCentralWidget(centralWidget)
        self.setWindowTitle('muSync')
        self.show()