from PyQt5.QtWidgets import QMainWindow, QWidget, QAction, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QMenuBar, QLabel, QComboBox, QDialog, QMessageBox, QListWidgetItem, QStatusBar
from PyQt5.QtCore import QCoreApplication, Qt
from PyQt5.QtGui import QIcon, QColor
import re, modules, icu, threading

class MainWindow(QMainWindow):
    __sources = {
        "left":  None,
        "right": None
    }
    __threads = {
        "left": None,
        "right": None,
        "compare": None
    }

    def __init__(self):
        super().__init__()
        self.buildUI()
        modules.load(self)

    def __bogus_module(self, module_name):
        errorMsg = QMessageBox(QMessageBox.Critical, "Bogus module", module_name + " module is not working properly", QMessageBox.Ok, self)
        errorMsg.show()

    def __compare_playlists(self):
        lList = self.findChild(QListWidget, "leftTracklist")
        rList = self.findChild(QListWidget, "rightTracklist")

        for i in range(lList.count()):
            self.statusBar().showMessage("Comparing tracklists ({} % completed).".format(round(100*i/lList.count())))
            l = lList.item(i)
            found = False
            for j in range(rList.count()):
                r = rList.item(j)
                # TODO make regexp configurable
                if re.sub(r'[^a-z]*', '', icu.Transliterator.createInstance('ASCII').transliterate(l.text()), flags=re.IGNORECASE).lower() == re.sub(r'[^a-z]*', '', icu.Transliterator.createInstance('ASCII').transliterate(r.text()), flags=re.IGNORECASE).lower():
                    found = True
                    l.setForeground(QColor(0, 127, 0))
                    r.setForeground(QColor(0, 127, 0))
                    l.track["peer"] = j
                    r.track["peer"] = i
                    break
            if not found:
                l.setForeground(QColor(127, 0, 0))

        self.statusBar().showMessage("Finished comparing tracks.")

        for i in range(rList.count()):
            r = rList.item(i)
            if r.foreground() != QColor(0, 127, 0):
                r.setForeground(QColor(127, 0, 0))

    def __load_tracks(self, source_name):
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

        # Check if the other playlist is also set to compare both
        if self.findChild(QComboBox, "{}Playlist".format("left" if source_name == "right" else "right")).currentData() is not None:
            thread = threading.Thread(target=self.__compare_playlists)
            self.__threads["compare"] = thread
            thread.start()

    def __playlist_select(self, source_name):
        for t in [source_name, "compare"]:
            # Stop any thread running on this source
            if self.__threads[t] is not None and self.__threads[t].isAlive():
                # TODO: for now we just wait for the thread to finish instead of stopping it
                self.__threads[t].join()

        # Remove links in the other tracklist to the ones in this one being removed
        otherList = self.findChild(QListWidget, "{}Tracklist".format("right" if source_name is "left" else "left"))
        for i in range(otherList.count()):
            peer = otherList.item(i)
            if "peer" in peer.track:
                del peer.track["peer"]

        thread = threading.Thread(target=self.__load_tracks, args=(source_name,))
        self.__threads[source_name] = thread
        thread.start()

    def __change_source(self, source_name, sourceDialog, sourcesList, sourceName):
        module_name = sourcesList.currentItem().text()
        module_slug = sourcesList.currentItem().slug
        if not module_slug in modules.modules:
            self.__bogus_module(module_name)
            return
        source = modules.modules[module_slug]
        if not source.isAuthenticated() and not source.authenticate(self):
            return False
        playlists = source.getPlaylists()
        if not playlists or len(playlists) == 0:
            self.__bogus_module(module_name)
            return
        self.findChild(QLabel, sourceName + "SourceLabel").setText("Selected source: " + module_name)
        self.__sources[sourceName] = modules.modules[module_slug]
        playlistSelect = self.findChild(QComboBox, source_name + "Playlist")
        playlistSelect.clear()
        playlistSelect.addItem("")
        for playlist in playlists:
            playlistSelect.addItem(playlist["name"], playlist["id"])
        sourceDialog.close()
        playlistSelect.setDisabled(False)
        self.findChild(QLabel, source_name + "PlaylistLabel").setDisabled(False)

    def __source_select(self, source_name):
        sources = modules.listAll()
        if len(sources) == 0:
            errorMsg = QMessageBox(QMessageBox.Critical, "No sources available", "No source modules found", QMessageBox.Ok, self)
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

    def __track_select(self, item):
        # If this track doesn't have a peer in the other tracklist, just finish
        if 'peer' not in item.track:
            return

        # Get this track's peer in the other tracklist and select it
        thisList = item.listWidget()
        otherList = self.findChild(QListWidget, "{}Tracklist".format("right" if thisList.objectName() == "leftTracklist" else "left"))

        otherItem = otherList.item(item.track["peer"])
        otherItem.setSelected(True)
        otherList.scrollToItem(otherItem)

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
        trackList.itemClicked.connect(self.__track_select)
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
        self.setStatusBar(QStatusBar(self))

        # Set tab order
        # It doesn't work :-(
        #QWidget.setTabOrder(exitBtn, leftSourceBtn)
        #QWidget.setTabOrder(leftSourceBtn, rightSourceBtn)
        #QWidget.setTabOrder(rightSourceBtn, leftTracklist)
        #QWidget.setTabOrder(leftList, rightTracklist)

        syncBtn.setFocus(Qt.OtherFocusReason)

        # Show window
        self.setCentralWidget(centralWidget)
        self.setWindowTitle('muSync')
        self.show()
