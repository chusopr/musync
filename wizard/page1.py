from wizard import WizardPage
from dialogs.accounts import AccountsDialog
import modules

from PySide6.QtWidgets import QWizard, QMessageBox, QFrame, QGridLayout, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QListWidget, QListWidgetItem
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt, Slot, Signal
import html
import re
import threading

_HAS_ICU = False
try:
    import icu
    _HAS_ICU = True
except ModuleNotFoundError:
    import unicodedata


class Page1(WizardPage):
    __threads = {
        0: None,
        1: None,
        "compare": None
    }
    __sources = [None, None]
    __items = [[], []]

    __change_next_tooltip = Signal(str)
    __tracklist_ready = Signal(int, int, list)
    __match_found = Signal(int, int, int, list)
    __match_not_found = Signal(int, int, list)
    __compare_finished = Signal(list)

    @Slot(str)
    def setNextButtonTooltip(self, str):
        self.parent().parent().parent().button(QWizard.NextButton).setToolTip(str)

    @Slot(modules.SourceModule)
    def __account_selected(self, side, account):
        account.status.connect(self.status.emit)
        account.log.connect(self.log.emit)

        if not account.isAuthenticated() and not account.authenticate(parent=self):
            QMessageBox(QMessageBox.Warning, "Authentication failed", """Authentication failed.

Possible causes:
* Wrong credentials.
* User cancelled.
* Module or server error.

Check the log for more details.""", QMessageBox.Ok, self).show()
            return

        playlists = account.getPlaylists()
        if playlists == []:
            QMessageBox(QMessageBox.Information, "No playlists found", """No playlists were found for this account.

Please choose another account which has playlists or create a playlist before choosing this account.""", QMessageBox.Ok, self).show()
            return

        if not playlists:
            QMessageBox(QMessageBox.Warning, "Unable to load playlists", """It was not possible to load the playlists for this account.

Possible causes:
* Module or server error.
* User cancelled.
* Wrong credentials.

Check the log for more details.""", QMessageBox.Ok, self).show()
            return

        self.setCompleted(False)

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
        self.findChild(QLabel, "PlaylistLabel{}".format(side)).setDisabled(False)

    @Slot(str)
    def __account_deleted(self, account):
        for side in [0, 1]:
            if self.__sources[side] is not None and self.__sources[side].getId() == account:
                self.setCompleted(False)
                playlistSelect = self.findChild(QComboBox, f"Playlist{side}")
                playlistSelect.setDisabled(True)
                playlistSelect.clear()
                playlistLabel = self.findChild(QLabel, f"PlaylistLabel{side}")
                playlistLabel.setDisabled(True)
                playlistLabel.setText("Selected playlist:")
                sourceLabel = self.findChild(QLabel, f"SourceLabel{side}")
                sourceLabel.setText("Selected account: None")
                sourceLabel.setToolTip("")
                self.__sources[side] = None

    @Slot(bool)
    def __account_select(self, side):
        source_modules = modules.listAll()
        if len(source_modules) == 0:
            errorMsg = QMessageBox(QMessageBox.Critical, "No sources available", "No source modules found", QMessageBox.Ok, self)
            errorMsg.show()
            return

        accountsDialog = AccountsDialog(self)
        accountsDialog.account_selected.connect(lambda account: self.__account_selected(side, account))
        accountsDialog.account_deleted.connect(lambda account: self.__account_deleted(account))
        accountsDialog.exec()
        del accountsDialog

    def __playlist_select(self, side):
        self.setCompleted(False)
        self.__loaded[side] = False

        # Wait for any comparison in progress so we don't replace songs being compared
        if self.__threads["compare"] is not None and self.__threads["compare"].is_alive():
            self.__threads["compare"].join()

        # Remove links in the other tracklist to the ones in this one being removed
        otherList = self.findChild(QListWidget, "Tracklist{}".format(int(not side)))
        for i in range(otherList.count()):
            peer = otherList.item(i)
            peer.setData(Qt.ForegroundRole, None)
            if "peer" in peer.track:
                del peer.track["peer"]

        self.setCompleted(False)

        # Add tracks to the tracklist in the main window
        trackList = self.findChild(QListWidget, "Tracklist{}".format(side))
        # Remove any entry from the previous playlist first
        while trackList.count() > 0:
            trackList.takeItem(0)

        # Set the cancel flag for the old thread
        if self.__cancel[side] is not None:
            self.__cancel[side].set()
        # Create a new cancel flag
        cancel = threading.Event()
        self.__cancel[side] = cancel

        self.__load_id[side] += 1
        self.__threads[side] = threading.Thread(
                target=self.__load_tracks,
                args=(
                    side,
                    self.__load_id[side],
                    cancel,
                    self.findChild(QComboBox, "Playlist{}".format(side)).currentData(),
                )
        )
        self.__threads[side].start()

    def __load_tracks(self, side, load_id, cancel, playlist_data):
        self.__change_next_tooltip.emit("")

        current_playlist = playlist_data["id"] if playlist_data is not None and "id" in playlist_data else None

        # No playlist actually selected
        if current_playlist is None:
            return

        # Get tracks for the current playlist
        tracks = self.__sources[side].getTracks(current_playlist, cancel)
        if cancel.is_set():
            return
        if tracks:
            self.__add_compare_keys(tracks)
        self.__tracklist_ready.emit(side, load_id, tracks)

    def getItems(self):
        return self.__items

    @Slot(int, int, list)
    def __add_tracks(self, side, load_id, tracks):
        # Check if these results correspond to the current request
        if load_id != self.__load_id[side]:
            return
        # Now add the tracks
        trackList = self.findChild(QListWidget, "Tracklist{}".format(side))

        self.__items[side] = []
        for t in tracks:
            self.__items[side].append(t)
            li = QListWidgetItem("{} - {}".format(t["artist"], t["title"]), trackList)
            li.track = t
            li.setToolTip(li.text())

        self.__loaded[side] = True

        p0 = self.findChild(QComboBox, "Playlist0")
        p1 = self.findChild(QComboBox, "Playlist1")
        t0 = self.findChild(QListWidget, "Tracklist0")
        t1 = self.findChild(QListWidget, "Tracklist1")

        # Check both playlists are set and loaded to compare them
        if not (
            p0.currentData() is None
            or p1.currentData() is None
            or not self.__loaded[int(not side)]
        ):
            # Check that at least one playlist is writable
            if self.__sources[0].getId() == self.__sources[1].getId() and p0.currentData()["id"] == p1.currentData()["id"]:
                self.status.emit("Both playlist are the same")
                self.__change_next_tooltip.emit("Cannot continue as both playlists are the same")
            elif not p0.currentData()["writable"] and not p1.currentData()["writable"]:
                self.status.emit("Both playlist are read-only")
                self.__change_next_tooltip.emit("Cannot continue as both playlists are read-only")
            else:
                # If there is some empty playlist, check it's not the only writable one
                if (t0.count() > 0 or p0.currentData()["writable"]) and (t1.count() > 0 or p1.currentData()["writable"]):
                    self.__threads["compare"] = threading.Thread(target=self.__compare_playlists)
                    self.__threads["compare"].start()
                else:
                    if t0.count() == 0:
                        p = p0.currentText()
                        a = self.__sources[0].getName()
                    else:
                        p = p1.currentText()
                        a = self.__sources[1].getName()
                    self.status.emit(f"Playlist {p} in {a} has no items and no new content can be added since it's read-only")
                    self.__change_next_tooltip.emit("The two selected playlists don't allow continuing")

    @Slot(int, int, int, list)
    def __highlight_match(self, side, pos, match, load_ids):
        if load_ids != self.__load_id:
            return
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

    @Slot(int, int, list)
    def __highlight_no_match(self, side, pos, load_ids):
        if load_ids != self.__load_id:
            return
        song = self.findChild(QListWidget, "Tracklist{}".format(side)).item(pos)
        song.setForeground(QColor(127, 0, 0))
        self.log.emit('Song <span style="color: #be0000">{}</span> from tracklist <strong>{}</strong> in <strong>{}</strong> not found in tracklist <strong>{}</strong> from <strong>{}</strong>'.format(
            html.escape(song.text()),
            html.escape(self.findChild(QComboBox, "Playlist{}".format(side)).currentText()),
            html.escape(self.__sources[side].getName()),
            html.escape(self.findChild(QComboBox, "Playlist{}".format(int(not side))).currentText()),
            html.escape(self.__sources[int(not side)].getName())
        ))

    def __add_compare_keys(self, tracks):
        transliterator = icu.Transliterator.createInstance('Any-Latin; Latin-ASCII') if _HAS_ICU else None
        for t in tracks:
            s = "{} - {}".format(t["artist"], t["title"])
            if _HAS_ICU:
                # Convert to latin alphabet
                s = transliterator.transliterate(s)
            else:
                # Decompose characters
                s = unicodedata.normalize("NFKD", s)
                # Remove combining characters
                s = "".join(c for c in s if not unicodedata.combining(c))
            # Remove anything that is not a letter or a number and switch to lowercase
            t["compare_key"] = re.sub(r'[\W_]+', '', s).casefold()

    def __compare_playlists(self):
        pos0 = pos1 = 0
        load_ids = list(self.__load_id)
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
            if song.get("peer") is not None:
                continue

            found = False

            if song["compare_key"] == "":
                self.__match_not_found.emit(side, pos, load_ids)
                continue

            for j in range(pos, len(self.__items[not side])):
                otherSong = self.__items[not side][j]
                if otherSong.get("peer") is not None:
                    continue
                if song["compare_key"] == otherSong["compare_key"]:
                    found = True
                    song["peer"] = j
                    otherSong["peer"] = pos
                    self.__match_found.emit(side, pos, j, load_ids)
                    break
            if not found:
                self.__match_not_found.emit(side, pos, load_ids)

        self.__compare_finished.emit(load_ids)

    @Slot(list)
    def __finish_comparing(self, load_ids):
        if self.__load_id == load_ids:
            self.status.emit("Finished comparing tracks.")
            self.setCompleted(True)

    @Slot(bool)
    def __unlink_songs(self):
        tl0 = self.findChild(QListWidget, "Tracklist0").currentItem()
        tl1 = self.findChild(QListWidget, "Tracklist1").currentItem()

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
        playlistSelect.currentTextChanged.connect(playlistSelect.setToolTip)
        selectedSourceLayout.addWidget(playlistSelect, 1, 1)
        sourceLayout.addWidget(selectedSourceFrame)

        trackList = QListWidget()
        trackList.setObjectName("Tracklist{}".format(side))
        trackList.currentItemChanged.connect(self.__track_select)
        sourceLayout.addWidget(trackList)
        return sourceLayout

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
        if not _HAS_ICU:
            print("PyICU was not found. It's recommended to install PyICU.")

        super().__init__()

        self.__load_id = [0, 0]
        self.__loaded = [False, False]
        self.__cancel = [None, None]
        self.__build_ui()

        self.__change_next_tooltip.connect(self.setNextButtonTooltip)
        self.__tracklist_ready.connect(self.__add_tracks)
        self.__match_found.connect(self.__highlight_match)
        self.__match_not_found.connect(self.__highlight_no_match)
        self.__compare_finished.connect(self.__finish_comparing)

    def getSources(self):
        return self.__sources

    def update(self):
        pass
