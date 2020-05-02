from PyQt5.QtWidgets import QMainWindow, QWidget, QAction, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QMenuBar, QLabel, QComboBox, QDialog, QMessageBox, QListWidgetItem
from PyQt5.QtCore import QCoreApplication, Qt
from PyQt5.QtGui import QIcon
import re, plugins

class MainWindow(QMainWindow):
    __sources = {
        "left":  None,
        "right": None
    }

    def __init__(self):
        super().__init__()
        self.buildUI()

    def __bogus_plugin(self, plugin_name):
        errorMsg = QMessageBox(QMessageBox.Critical, "Bogus plugin", plugin_name + " plugin is not working properly", QMessageBox.Ok, self)
        errorMsg.show()

    def __playlist_select(self, source_name):
        current_playlist = self.findChild(QComboBox, source_name + "Playlist").currentData()

        # No playlist actually selected
        if current_playlist == None:
            return

        # Get tracks for the current playlist
        tracks = self.__sources[source_name].getTracks(current_playlist)
        # No tracks returned for the current playlist. Do nothing.
        # TODO Should we do something? Maybe show an error message
        if not tracks:
            return

        # Add tracks to the tracklist in the main window
        trackList = self.findChild(QListWidget, source_name + "Tracklist")
        # Remove any entry from the previous playlist first
        while trackList.count() > 0:
            trackList.takeItem(0)
        # Now add the tracks
        for t in tracks:
            QListWidgetItem("%s - %s" % (t["artist"], t["title"]), trackList).track = t

    def __change_source(self, source_name, sourceDialog, sourcesList, sourceName):
        plugin_name = sourcesList.currentItem().text()
        plugin_slug = sourcesList.currentItem().slug
        if not plugin_slug in plugins.plugins:
            self.__bogus_plugin(plugin_name)
            return
        source = plugins.plugins[plugin_slug]
        if not source.isAuthenticated() and not source.authenticate(self):
            return False
        playlists = source.getPlaylists()
        if not playlists or len(playlists) == 0:
            self.__bogus_plugin(plugin_name)
            return
        self.findChild(QLabel, sourceName + "SourceLabel").setText("Selected source: " + plugin_name)
        self.__sources[sourceName] = plugins.plugins[plugin_slug]
        playlistSelect = self.findChild(QComboBox, source_name + "Playlist")
        playlistSelect.addItem("")
        for playlist in playlists:
            playlistSelect.addItem(playlist["name"], playlist["id"])
        sourceDialog.close()
        playlistSelect.setDisabled(False)
        self.findChild(QLabel, source_name + "PlaylistLabel").setDisabled(False)

    def __source_select(self, source_name):
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
        okButton.clicked.connect(lambda: self.__change_source(source_name, sourceDialog, sourcesList, sourceName))
        buttonsLayout.addWidget(okButton)
        cancelButton = QPushButton(QIcon.fromTheme("dialog-cancel"), "&Cancel")
        cancelButton.clicked.connect(sourceDialog.close)
        buttonsLayout.addWidget(cancelButton)
        dialogLayout.addLayout(buttonsLayout)
        for source in sources.items():
            sourceItem = QListWidgetItem(source[1])
            sourceItem.slug = source[0]
            sourcesList.addItem(sourceItem)
        sourcesList.itemDoubleClicked.connect(lambda: self.__change_source(source_name, sourceDialog, sourcesList, sourceName))
        sourceDialog.show()

    def __create_source_layout(self, source_name):
        sourceLayout = QVBoxLayout()
        selectedSourceLayout = QHBoxLayout()
        sourceLabel = QLabel("Selected source: None")
        sourceLabel.setObjectName(source_name + "SourceLabel")
        selectedSourceLayout.addWidget(sourceLabel, 1)
        changeSourceBtn = QPushButton("Change...")
        changeSourceBtn.setObjectName(source_name + "SourceBtn")
        changeSourceBtn.clicked.connect(lambda: self.__source_select(source_name))
        selectedSourceLayout.addWidget(changeSourceBtn)
        playlistLabel = QLabel("Selected playlist:")
        playlistLabel.setObjectName(source_name + "PlaylistLabel")
        playlistLabel.setDisabled(True)
        selectedSourceLayout.addWidget(playlistLabel)
        playlistSelect = QComboBox()
        playlistSelect.setDisabled(True)
        playlistSelect.setObjectName(source_name + "Playlist")
        playlistSelect.currentIndexChanged.connect(lambda: self.__playlist_select(source_name))
        selectedSourceLayout.addWidget(playlistSelect, 1)
        sourceLayout.addLayout(selectedSourceLayout)

        trackList = QListWidget()
        trackList.setObjectName(source_name + "Tracklist")
        sourceLayout.addWidget(trackList)
        return (sourceLayout, playlistSelect, trackList, changeSourceBtn)

    def __start_sync(self):
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

        leftLayout, leftPlaylist, leftTracklist, leftSourceBtn = self.__create_source_layout("left")
        mainLayout.addLayout(leftLayout)
        rightLayout, rightPlaylist, rightTracklist, rightSourceBtn = self.__create_source_layout("right")
        mainLayout.addLayout(rightLayout)

        windowLayout.addLayout(mainLayout, 1)

        buttonsWidget = QWidget()
        buttonsLayout = QHBoxLayout(buttonsWidget)
        syncBtn = QPushButton(QIcon.fromTheme("system-run"), "S&ync")
        syncBtn.clicked.connect(self.__start_sync)
        buttonsLayout.addWidget(syncBtn, 1, Qt.AlignRight)
        settingsBtn = QPushButton(QIcon.fromTheme("preferences-other"), "&Settings")
        buttonsLayout.addWidget(settingsBtn, 1, Qt.AlignRight)
        exitBtn = QPushButton(QIcon.fromTheme("window-close"), "Quit")
        exitBtn.clicked.connect(QCoreApplication.instance().quit)
        buttonsLayout.addWidget(exitBtn, 1, Qt.AlignRight)
        windowLayout.addWidget(buttonsWidget, 0, Qt.AlignRight)

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
