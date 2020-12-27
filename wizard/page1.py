from wizard import WizardPage
from dialogs.accounts import AccountsDialog
import modules

from PySide2.QtWidgets import QWizard, QMessageBox, QFrame, QGridLayout, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QListWidget, QListWidgetItem
from PySide2.QtGui import QColor
from PySide2.QtCore import QSettings, Slot, Signal
import json
import html
import re
import os
import threading
from sys import stderr, modules as imported_modules

try:
    import icu
except ModuleNotFoundError:
    pass


class Page1(WizardPage):
    __threads = {
        0: None,
        1: None,
        "compare": None
    }
    __sources = [None, None]
    __items = [[], []]

    __change_next_tooltip = Signal(str)
    __tracklist_ready = Signal(int, list)
    __match_found = Signal(int, int, int)
    __match_not_found = Signal(int, int)
    __compare_finished = Signal()

    @Slot(str)
    def setNextButtonTooltip(self, str):
        self.parent().parent().parent().button(QWizard.NextButton).setToolTip(str)

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
            return  # TODO do something else than silently fail

        self.findChild(QLabel, "SourceLabel{}".format(side)).setText("Selected account: " + account.getName())
        self.findChild(QLabel, "SourceLabel{}".format(side)).setToolTip("Selected account: " + account.getName())
        self.parent().parent().parent().resize(self.parent().parent().parent().sizeHint())
        self.__sources[side] = account
        playlistSelect = self.findChild(QComboBox, "Playlist{}".format(side))
        playlistSelect.clear()
        playlistSelect.addItem("")
        for playlist in playlists:
            playlistSelect.addItem(playlist["name"], playlist)
        playlistSelect.setDisabled(False)
        playlistSelect.currentTextChanged.connect(playlistSelect.setToolTip)
        self.findChild(QLabel, "PlaylistLabel{}".format(side)).setDisabled(False)

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
        otherList = self.findChild(QListWidget, "Tracklist{}".format(int(not side)))
        for i in range(otherList.count()):
            peer = otherList.item(i)
            if "peer" in peer.track:
                del peer.track["peer"]

        self.setCompleted(False)

        # Add tracks to the tracklist in the main window
        trackList = self.findChild(QListWidget, "Tracklist{}".format(side))
        # Remove any entry from the previous playlist first
        while trackList.count() > 0:
            trackList.takeItem(0)

        self.__threads[side] = threading.Thread(target=self.__load_tracks, args=(side, self.findChild(QComboBox, "Playlist{}".format(side)).currentData(),))
        self.__threads[side].start()

    def __load_tracks(self, side, playlist_data):
        self.__change_next_tooltip.emit("")

        current_playlist = playlist_data["id"] if playlist_data is not None and "id" in playlist_data else None

        # No playlist actually selected
        if current_playlist is None:
            return

        # Get tracks for the current playlist
        tracks = self.__sources[side].getTracks(current_playlist)
        self.__tracklist_ready.emit(side, tracks)

    def getItems(self):
        return self.__items

    @Slot(int, list)
    def __add_tracks(self, side, tracks):
        # Now add the tracks
        trackList = self.findChild(QListWidget, "Tracklist{}".format(side))

        self.__items[side] = []
        for t in tracks:
            self.__items[side].append(t)
            li = QListWidgetItem("{} - {}".format(t["artist"], t["title"]), trackList)
            li.track = t
            li.setToolTip(li.text())

        p0 = self.findChild(QComboBox, "Playlist0")
        p1 = self.findChild(QComboBox, "Playlist1")
        t0 = self.findChild(QListWidget, "Tracklist0")
        t1 = self.findChild(QListWidget, "Tracklist1")

        # Check both playlists are set and loaded to compare them
        if not (
            p0.currentData() is None
            or p1.currentData() is None
            or self.__threads[0].isAlive()
            or self.__threads[1].isAlive()
        ):
            # Check that at least one playlist is writable
            if p0.currentData()["writable"] or p1.currentData()["writable"]:
                # If there is some empty playlist, check it's not the only writable one
                if (t0.count() > 0 or p0.currentData()["writable"]) and (t1.count() > 0 or p1.currentData()["writable"]):
                    self.__threads["compare"] = threading.Thread(target=self.__compare_playlists)
                    self.__threads["compare"].start()
                else:
                    if t0.count() == 0:
                        p = p0.currentText()
                        a = self.findChild(QLabel, "SourceLabel0").text()
                    else:
                        p = p1.currentText()
                        a = self.findChild(QLabel, "SourceLabel1").text()
                    self.status.emit("Playlist {} in {} has no items and no new content can be added since it's read-only".format(p, a))
                    self.__change_next_tooltip.emit("The two selected playlists don't allow continuing")
            else:
                self.status.emit("Both playlist are read-only")
                self.__change_next_tooltip.emit("Cannot continue as both playlists are read-only")

    @Slot(int, int, int)
    def __highlight_match(self, side, pos, match):
        song = self.findChild(QListWidget, "Tracklist{}".format(side)).item(pos)
        otherSong = self.findChild(QListWidget, "Tracklist{}".format(int(not side))).item(match)
        song.setForeground(QColor(0, 127, 0))
        otherSong.setForeground(QColor(0, 127, 0))
        self.log.emit('Song <span style="color: #00be00">{}</span> from tracklist <strong>{}</strong> in <strong>{}</strong> found as <span style="color: #00be00">{}</span> in tracklist <strong>{}</strong> from <strong>{}</strong>'.format(
            html.escape(song.text()),
            html.escape(self.findChild(QComboBox, "Playlist{}".format(side)).currentText()),
            html.escape(self.__sources[side].getName()),
            html.escape(otherSong.text()),
            html.escape(self.findChild(QComboBox, "Playlist{}".format(int(not side))).currentText()),
            html.escape(self.__sources[int(not side)].getName())
        ))

    @Slot(int, int)
    def __highlight_no_match(self, side, pos):
        song = self.findChild(QListWidget, "Tracklist{}".format(side)).item(pos)
        song.setForeground(QColor(127, 0, 0))
        self.log.emit('Song <span style="color: #be0000">{}</span> from tracklist <strong>{}</strong> in <strong>{}</strong> not found in tracklist <strong>{}</strong> from <strong>{}</strong>'.format(
            html.escape(song.text()),
            html.escape(self.findChild(QComboBox, "Playlist{}".format(side)).currentText()),
            html.escape(self.__sources[side].getName()),
            html.escape(self.findChild(QComboBox, "Playlist{}".format(int(not side))).currentText()),
            html.escape(self.__sources[int(not side)].getName())
        ))

    def __compare_playlists(self):
        pos0 = pos1 = 0
        while pos0 < len(self.__items[0]) or pos1 < len(self.__items[1]):
            self.status.emit("Comparing tracklists ({} % completed).".format(round((pos0 + pos1) * 100 / (len(self.__items[0]) + len(self.__items[1])))))

            if (pos0 < pos1 and pos0 < len(self.__items[0])) or ((pos0 >= pos1) and (pos1 >= len(self.__items[1]))):
                side = 0
                pos = pos0
                pos0 += 1
            else:
                side = 1
                pos = pos1
                pos1 += 1

            song = self.__items[side][pos]
            if "peer" in song and song["peer"]:
                continue

            found = False

            for j in range(pos, len(self.__items[not side])):
                otherSong = self.__items[not side][j]
                # TODO make regexp configurable
                if re.sub(r'[^a-z]*', '', icu.Transliterator.createInstance('ASCII').transliterate("{} - {}".format(song["artist"], song["title"])) if "icu" in imported_modules else "{} - {}".format(song["artist"], song["title"]), flags=re.IGNORECASE).lower() == re.sub(r'[^a-z]*', '', icu.Transliterator.createInstance('ASCII').transliterate("{} - {}".format(otherSong["artist"], otherSong["title"])) if "icu" in imported_modules else "{} - {}".format(otherSong["artist"], otherSong["title"]), flags=re.IGNORECASE).lower():
                    found = True
                    song["peer"] = j
                    otherSong["peer"] = pos
                    self.__match_found.emit(side, pos, j)
                    break
            if not found:
                self.__match_not_found.emit(side, pos)

        # FIXME: Should only be run when both tracklists finished downloading
        self.status.emit("Finished comparing tracks.")
        self.__compare_finished.emit()

    @Slot(bool)
    def __unlink_songs(self):
        tl0 = self.findChild(QListWidget, "Tracklist0").currentItem()
        tl1 = self.findChild(QListWidget, "Tracklist1").currentItem()

        # Weird: for some reason, one of l.track and r.track is always None
        if tl0 is None:
            tl0 = self.findChild(QListWidget, "Tracklist0").item(tl1.track["peer"])
        elif tl1 is None:
            tl1 = self.findChild(QListWidget, "Tracklist1").item(tl0.track["peer"])

        tl0.track["peer"] = tl1.track["peer"] = None
        tl0.setForeground(QColor(127, 0, 0))
        tl1.setForeground(QColor(127, 0, 0))

    def __track_select(self, item):
        thisList = item.listWidget()
        otherList = self.findChild(QListWidget, "Tracklist{}".format("0" if thisList.objectName() == "Tracklist1" else "1"))
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
        sourceLabel.setObjectName("SourceLabel{}".format(side))
        selectedSourceLayout.addWidget(sourceLabel, 0, 0)
        changeSourceBtn = QPushButton("Change...")
        changeSourceBtn.clicked.connect(lambda: self.__account_select(side))
        selectedSourceLayout.addWidget(changeSourceBtn, 0, 1)
        playlistLabel = QLabel("Selected playlist:")
        playlistLabel.setObjectName("PlaylistLabel{}".format(side))
        playlistLabel.setDisabled(True)
        selectedSourceLayout.addWidget(playlistLabel, 1, 0)
        playlistSelect = QComboBox()
        playlistSelect.setDisabled(True)
        playlistSelect.setObjectName("Playlist{}".format(side))
        playlistSelect.currentIndexChanged.connect(lambda: self.__playlist_select(side))
        selectedSourceLayout.addWidget(playlistSelect, 1, 1)
        sourceLayout.addWidget(selectedSourceFrame)

        trackList = QListWidget()
        trackList.setObjectName("Tracklist{}".format(side))
        trackList.currentItemChanged.connect(self.__track_select)
        sourceLayout.addWidget(trackList)
        return sourceLayout

    def getSource(self, s):
        return self._sources[s]

    def __build_ui(self):
        page1Layout = QVBoxLayout(self)

        sourcesLayout = QHBoxLayout()
        page1Layout.addLayout(sourcesLayout)

        sourcesLayout.addLayout(self.__create_source_layout(0))

        unlinkButton = QPushButton("Unlink")
        unlinkButton.setObjectName("unlinkButton")
        unlinkButton.setDisabled(True)
        unlinkButton.setToolTip("Unlink songs")
        unlinkButton.clicked.connect(self.__unlink_songs)
        sourcesLayout.addWidget(unlinkButton)

        sourcesLayout.addLayout(self.__create_source_layout(1))

    def __init__(self):
        if "icu" not in imported_modules:
            print("PyICU was not found. It's recommended to isntall PyICU.")

        super().__init__()

        self.__build_ui()

        self.__change_next_tooltip.connect(self.setNextButtonTooltip)
        self.__tracklist_ready.connect(self.__add_tracks)
        self.__match_found.connect(self.__highlight_match)
        self.__match_not_found.connect(self.__highlight_no_match)
        self.__compare_finished.connect(lambda: self.setCompleted(True))

    def getSources(self):
        return self.__sources

    def update(self):
        pass
