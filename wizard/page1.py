from wizard import WizardPage
from wizard.page2 import Page2
from dialogs.accounts import AccountsDialog
import modules

from PyQt5.QtWidgets import QMessageBox, QWizard, QVBoxLayout, QHBoxLayout, QStatusBar, QLabel, QPushButton, QComboBox, QListWidget, QListWidgetItem
import re, threading

class Page1(WizardPage):
    __threads = {
        "left": None,
        "right": None,
        "compare": None
    }
    __parent = None

    def __account_select(self, source_name):
        source_modules = modules.listAll()
        if len(source_modules) == 0:
            errorMsg = QMessageBox(QMessageBox.Critical, "No sources available", "No source modules found", QMessageBox.Ok, self)
            errorMsg.show()
            return

        sourceName = re.sub(r"SourceBtn$", "", self.sender().objectName())
        accountsDialog = AccountsDialog(self.__parent, source_name)

    def __playlist_select(self, source_name):
        self.__completed = False

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

    def __load_tracks(self, source_name):
        self.__completed = False

        current_playlist = self.findChild(QComboBox, source_name + "Playlist").currentData()

        # No playlist actually selected
        if current_playlist == None:
            return

        # Get tracks for the current playlist
        tracks = self.__parent._sources[source_name].getTracks(current_playlist)
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
            QListWidgetItem("{} - {}".format(t["artist"], t["title"]), trackList).track = t

        # Check if the other playlist is also set to compare both
        if self.findChild(QComboBox, "{}Playlist".format("left" if source_name == "right" else "right")).currentData() is not None:
            thread = threading.Thread(target=self.__parent._compare_playlists)
            self.__threads["compare"] = thread
            thread.start()

    def __track_select(self, item):
        thisList = item.listWidget()
        otherList = self.findChild(QListWidget, "{}Tracklist".format("right" if thisList.objectName() == "leftTracklist" else "left"))

        # If this track doesn't have a peer in the other tracklist, just finish
        if 'peer' not in item.track:
            otherList.setCurrentItem(None)
            return

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
        changeSourceBtn.clicked.connect(lambda: self.__account_select(source_name))
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

    def __init__(self, parent):
        super().__init__()
        self.__parent = parent

        page1Layout = QVBoxLayout(self)

        sourcesLayout = QHBoxLayout()
        page1Layout.addLayout(sourcesLayout)

        leftLayout, leftPlaylist, leftTracklist, leftSourceBtn = self.__create_source_layout("left")
        sourcesLayout.addLayout(leftLayout)
        rightLayout, rightPlaylist, rightTracklist, rightSourceBtn = self.__create_source_layout("right")
        sourcesLayout.addLayout(rightLayout)

        statusBar = QStatusBar(self)
        statusBar.setObjectName("statusBar")
        statusBar.messageChanged.connect(parent._status_updated)

        page1Layout.addWidget(statusBar)

        page2 = Page2()
        parent.addPage(self)
        parent.addPage(page2)

    def update(self):
        pass
