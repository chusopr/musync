from wizard import WizardPage
from dialogs.accounts import AccountsDialog
import modules

from PySide2.QtWidgets import QMessageBox, QFrame, QGridLayout, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QListWidget, QListWidgetItem
from PySide2.QtGui import QColor
from PySide2.QtCore import QSettings, Slot
import html, json, os, re, threading
from sys import stderr, modules as imported_modules

try:
    import icu
except ModuleNotFoundError:
    pass

class Page1(WizardPage):
    __threads = {
        "left": None,
        "right": None,
        "compare": None
    }
    __sources = {
        "left":  None,
        "right": None
    }

    @Slot(modules.SourceModule)
    def __account_added(self, account):
        account.status.connect(self.status.emit)

    @Slot(modules.SourceModule)
    def __account_selected(self, side, account):
        self.setCompleted(False)

        account.status.connect(self.status.emit)
        account.log.connect(self.log.emit)

        if not account.isAuthenticated() and not account.authenticate():
            # TODO show error
            return False

        playlists = account.getPlaylists()
        if not playlists or len(playlists) == 0:
            return # TODO do something else than silently fail

        self.findChild(QLabel, side + "SourceLabel").setText("Selected account: " + account.getName())
        self.findChild(QLabel, side + "SourceLabel").setToolTip("Selected account: " + account.getName())
        self.parent().parent().parent().resize(self.parent().parent().parent().sizeHint())
        self.__sources[side] = account
        playlistSelect = self.findChild(QComboBox, side + "Playlist")
        playlistSelect.clear()
        playlistSelect.addItem("")
        for playlist in playlists:
            playlistSelect.addItem(playlist["name"], playlist)
        playlistSelect.setDisabled(False)
        playlistSelect.currentTextChanged.connect(playlistSelect.setToolTip)
        self.findChild(QLabel, side + "PlaylistLabel").setDisabled(False)

    @Slot(bool)
    def __account_select(self, side):
        source_modules = modules.listAll()
        if len(source_modules) == 0:
            errorMsg = QMessageBox(QMessageBox.Critical, "No sources available", "No source modules found", QMessageBox.Ok, self)
            errorMsg.show()
            return

        accountsDialog = AccountsDialog()
        accountsDialog.account_added.connect(self.__account_added)
        accountsDialog.account_selected.connect(lambda account: self.__account_selected(side, account))
        accountsDialog.exec()
        del accountsDialog

    def __playlist_select(self, side):
        self.setCompleted(False)

        for t in [side, "compare"]:
            # Stop any thread running on this source
            if self.__threads[t] is not None and self.__threads[t].is_alive():
                # TODO: for now we just wait for the thread to finish instead of stopping it
                self.__threads[t].join()

        # Remove links in the other tracklist to the ones in this one being removed
        otherList = self.findChild(QListWidget, "{}Tracklist".format("right" if side == "left" else "left"))
        for i in range(otherList.count()):
            peer = otherList.item(i)
            if "peer" in peer.track:
                del peer.track["peer"]

        thread = threading.Thread(target=self.__load_tracks, args=(side,))
        self.__threads[side] = thread
        thread.start()

    def __load_tracks(self, side):
        self.setCompleted(False)

        playlist_data = self.findChild(QComboBox, side + "Playlist").currentData()

        current_playlist = playlist_data["id"] if playlist_data is not None and "id" in playlist_data else None

        # No playlist actually selected
        if current_playlist == None:
            return

        # Get tracks for the current playlist
        tracks = self.__sources[side].getTracks(current_playlist)
        # No tracks returned for the current playlist. Do nothing.
        # TODO Should we do something? Maybe show an error message
        if not tracks:
            return

        # Add tracks to the tracklist in the main window
        trackList = self.findChild(QListWidget, side + "Tracklist")
        # Remove any entry from the previous playlist first
        while trackList.count() > 0:
            trackList.takeItem(0)
        # Now add the tracks
        for t in tracks:
            li = QListWidgetItem("{} - {}".format(t["artist"], t["title"]), trackList)
            li.track = t
            li.setToolTip(li.text())

        # Check if the other playlist is also set to compare both
        if self.findChild(QListWidget, "{}Tracklist".format("left" if side == "right" else "right")).count() > 0:
            thread = threading.Thread(target=self.__compare_playlists)
            self.__threads["compare"] = thread
            thread.start()

    def __compare_playlists(self):
        self.setCompleted(False)
        lList = self.findChild(QListWidget, "leftTracklist")
        rList = self.findChild(QListWidget, "rightTracklist")

        lPos = rPos = 0
        while lPos < lList.count() or rPos < rList.count():
            self.status.emit("Comparing tracklists ({} % completed).".format(round((lPos+rPos)*100/(lList.count()+rList.count()))))
            if (lPos < rPos and lPos < lList.count()) or ((lPos >= rPos) and (rPos >= rList.count())):
                thisList = lList
                otherList = rList
                pos = lPos
                song = lList.item(pos)
                lPos = lPos + 1
                side = 0
            else:
                thisList = rList
                otherList = lList
                pos = rPos
                song = rList.item(pos)
                rPos = rPos + 1
                side = 1

            if "peer" in song.track and song.track["peer"]:
                continue

            found = False
            for j in range(pos, otherList.count()):
                otherSong = otherList.item(j)
                # TODO make regexp configurable
                if re.sub(r'[^a-z]*', '', icu.Transliterator.createInstance('ASCII').transliterate(song.text()) if "icu" in imported_modules else song.text(), flags=re.IGNORECASE).lower() == re.sub(r'[^a-z]*', '', icu.Transliterator.createInstance('ASCII').transliterate(otherSong.text()) if "icu" in imported_modules else otherSong.text(), flags=re.IGNORECASE).lower():
                    found = True
                    song.setForeground(QColor(0, 127, 0))
                    otherSong.setForeground(QColor(0, 127, 0))
                    song.track["peer"] = j
                    otherSong.track["peer"] = pos
                    self.log.emit('Song <span style="color: #00be00">{}</span> from tracklist <strong>{}</strong> in <strong>{}</strong> found as <span style="color: #00be00">{}</span> in tracklist <strong>{}</strong> from <strong>{}</strong>'.format(
                        html.escape(song.text()),
                        html.escape(self.findChild(QComboBox, "{}Playlist".format("right" if side else "left")).currentText()),
                        html.escape(self.__sources["right" if side else "left"].getName()),
                        html.escape(otherSong.text()),
                        html.escape(self.findChild(QComboBox, "{}Playlist".format("left" if side else "left")).currentText()),
                        html.escape(self.__sources["left" if side else "right"].getName())
                    ))
                    break
            if not found:
                song.setForeground(QColor(127, 0, 0))
                self.log.emit('Song <span style="color: #be0000">{}</span> from tracklist <strong>{}</strong> in <strong>{}</strong> not found in tracklist <strong>{}</strong> from <strong>{}</strong>'.format(
                    html.escape(song.text()),
                    html.escape(self.findChild(QComboBox, "{}Playlist".format("right" if side else "left")).currentText()),
                    html.escape(self.__sources["right" if side else "left"].getName()),
                    html.escape(self.findChild(QComboBox, "{}Playlist".format("left" if side else "left")).currentText()),
                    html.escape(self.__sources["left" if side else "right"].getName())
                ))

        # FIXME: Should only be run when both tracklists finished downloading
        self.status.emit("Finished comparing tracks.")
        self.setCompleted(True)

    @Slot(bool)
    def __unlink_songs(self):
        l = self.findChild(QListWidget, "leftTracklist").currentItem()
        r = self.findChild(QListWidget, "rightTracklist").currentItem()

        # Weird: for some reason, one of l.track and r.track is always None
        if l is None:
            l = self.findChild(QListWidget, "leftTracklist").item(r.track["peer"])
        elif r is None:
            r = self.findChild(QListWidget, "rightTracklist").item(l.track["peer"])

        l.track["peer"] = r.track["peer"] = None
        l.setForeground(QColor(127, 0, 0))
        r.setForeground(QColor(127, 0, 0))

    def __track_select(self, item):
        thisList = item.listWidget()
        otherList = self.findChild(QListWidget, "{}Tracklist".format("right" if thisList.objectName() == "leftTracklist" else "left"))
        unlinkButton = self.findChild(QPushButton, "unlinkButton")

        # If this track doesn't have a peer in the other tracklist, just finish
        if 'peer' not in item.track or item.track["peer"] is None:
            otherList.setCurrentItem(None)
            unlinkButton.setDisabled(True)
            return

        otherItem = otherList.item(item.track["peer"])
        otherItem.setSelected(True)
        otherList.scrollToItem(otherItem)
        unlinkButton.setDisabled(False)

    def __create_source_layout(self, side):
        sourceLayout = QVBoxLayout()
        selectedSourceFrame = QFrame()
        selectedSourceFrame.setFrameShape(QFrame.Box)
        selectedSourceFrame.setFrameShadow(QFrame.Raised)
        selectedSourceLayout = QGridLayout(selectedSourceFrame)
        sourceLabel = QLabel("Selected account: None")
        sourceLabel.setObjectName(side + "SourceLabel")
        selectedSourceLayout.addWidget(sourceLabel, 0, 0)
        changeSourceBtn = QPushButton("Change...")
        changeSourceBtn.setObjectName(side + "SourceBtn")
        changeSourceBtn.clicked.connect(lambda: self.__account_select(side))
        selectedSourceLayout.addWidget(changeSourceBtn, 0, 1)
        playlistLabel = QLabel("Selected playlist:")
        playlistLabel.setObjectName(side + "PlaylistLabel")
        playlistLabel.setDisabled(True)
        selectedSourceLayout.addWidget(playlistLabel, 1, 0)
        playlistSelect = QComboBox()
        playlistSelect.setDisabled(True)
        playlistSelect.setObjectName(side + "Playlist")
        playlistSelect.currentIndexChanged.connect(lambda: self.__playlist_select(side))
        selectedSourceLayout.addWidget(playlistSelect, 1, 1)
        sourceLayout.addWidget(selectedSourceFrame)

        trackList = QListWidget()
        trackList.setObjectName(side + "Tracklist")
        trackList.currentItemChanged.connect(self.__track_select)
        sourceLayout.addWidget(trackList)
        return sourceLayout

    def getSource(self, s):
        return self._sources[s]

    def __build_ui(self):
        page1Layout = QVBoxLayout(self)

        sourcesLayout = QHBoxLayout()
        page1Layout.addLayout(sourcesLayout)

        sourcesLayout.addLayout(self.__create_source_layout("left"))

        unlinkButton = QPushButton("Unlink")
        unlinkButton.setObjectName("unlinkButton")
        unlinkButton.setDisabled(True)
        unlinkButton.setToolTip("Unlink songs")
        unlinkButton.clicked.connect(self.__unlink_songs)
        sourcesLayout.addWidget(unlinkButton)

        sourcesLayout.addLayout(self.__create_source_layout("right"))

    def __init__(self):
        if "icu" not in imported_modules:
            print("PyICU was not found. It's recommended to isntall PyICU.")

        super().__init__()

        self.__build_ui()

    def getSources(self):
        return self.__sources

    def update(self):
        pass
