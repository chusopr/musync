from wizard import WizardPage
from wizard.page2 import Page2
from dialogs.accounts import AccountsDialog
import modules

from PyQt5.QtWidgets import QMessageBox, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QListWidget, QListWidgetItem
from PyQt5.QtGui import QColor
import cgi, icu, json, os, re, threading
from appdirs import user_config_dir
from sys import stderr

class Page1(WizardPage):
    __threads = {
        "left": None,
        "right": None,
        "compare": None
    }
    __accounts_file = os.path.join(user_config_dir("musync"), "accounts.json")
    __accounts = {}
    __sources = {
        "left":  None,
        "right": None
    }

    def __save_settings(self):
        s = {}
        for k,v in self.__accounts.items():
            s[k] = v.getType()
        os.makedirs(os.path.dirname(self.__accounts_file), 0o700, True)
        with open(self.__accounts_file, "w") as f:
            json.dump(s, f)

    def __account_added(self, account):
        self.__accounts[account.getId()] = account
        self.__save_settings()
        account.status.connect(self.status.emit)

    def __account_deleted(self, account_id):
        del self.__accounts[account_id]
        self.__save_settings()

    def __account_selected(self, side, account):
        self.setCompleted(False)

        if not account.isAuthenticated() and not account.authenticate():
            # TODO show error
            return False

        playlists = account.getPlaylists()
        if not playlists or len(playlists) == 0:
            return # TODO do something else than silently fail

        self.findChild(QLabel, side + "SourceLabel").setText("Selected source: " + account.getName())
        self.findChild(QLabel, side + "SourceLabel").setToolTip("Selected source: " + account.getName())
        self.__sources[side] = account
        playlistSelect = self.findChild(QComboBox, side + "Playlist")
        playlistSelect.clear()
        playlistSelect.addItem("")
        for playlist in playlists:
            playlistSelect.addItem(playlist["name"], playlist["id"])
        playlistSelect.setDisabled(False)
        playlistSelect.currentTextChanged.connect(playlistSelect.setToolTip)
        self.findChild(QLabel, side + "PlaylistLabel").setDisabled(False)

    def __account_select(self, side):
        source_modules = modules.listAll()
        if len(source_modules) == 0:
            errorMsg = QMessageBox(QMessageBox.Critical, "No sources available", "No source modules found", QMessageBox.Ok, self)
            errorMsg.show()
            return

        accountsDialog = AccountsDialog(self.__accounts)
        accountsDialog.account_added.connect(self.__account_added)
        accountsDialog.account_deleted.connect(self.__account_deleted)
        accountsDialog.account_selected.connect(lambda account: self.__account_selected(side, account))
        del accountsDialog

    def __playlist_select(self, side):
        self.setCompleted(False)

        for t in [side, "compare"]:
            # Stop any thread running on this source
            if self.__threads[t] is not None and self.__threads[t].isAlive():
                # TODO: for now we just wait for the thread to finish instead of stopping it
                self.__threads[t].join()

        # Remove links in the other tracklist to the ones in this one being removed
        otherList = self.findChild(QListWidget, "{}Tracklist".format("right" if side is "left" else "left"))
        for i in range(otherList.count()):
            peer = otherList.item(i)
            if "peer" in peer.track:
                del peer.track["peer"]

        thread = threading.Thread(target=self.__load_tracks, args=(side,))
        self.__threads[side] = thread
        thread.start()

    def __load_tracks(self, side):
        self.setCompleted(False)

        current_playlist = self.findChild(QComboBox, side + "Playlist").currentData()

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
        if self.findChild(QComboBox, "{}Playlist".format("left" if side == "right" else "right")).currentData() is not None:
            thread = threading.Thread(target=self.__compare_playlists)
            self.__threads["compare"] = thread
            thread.start()

    def __compare_playlists(self):
        self.setCompleted(False)
        lList = self.findChild(QListWidget, "leftTracklist")
        rList = self.findChild(QListWidget, "rightTracklist")

        lPos = rPos = 0
        while lPos < lList.count() or rPos < rList.count():
            self.status.emit("Comparing tracklists ({} % completed).".format(int((lPos+rPos)*100/(lList.count()+rList.count()))))
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
                if re.sub(r'[^a-z]*', '', icu.Transliterator.createInstance('ASCII').transliterate(song.text()), flags=re.IGNORECASE).lower() == re.sub(r'[^a-z]*', '', icu.Transliterator.createInstance('ASCII').transliterate(otherSong.text()), flags=re.IGNORECASE).lower():
                    found = True
                    song.setForeground(QColor(0, 127, 0))
                    otherSong.setForeground(QColor(0, 127, 0))
                    song.track["peer"] = j
                    otherSong.track["peer"] = pos
                    self.log.emit('Song <span style="color: #00be00">{}</span> from tracklist <strong>{}</strong> in <strong>{}</strong> found as <span style="color: #00be00">{}</span> in tracklist <strong>{}</strong> from <strong>{}</strong>'.format(
                        cgi.escape(song.text()),
                        cgi.escape(self.findChild(QComboBox, "{}Playlist".format("right" if side else "left")).currentText()),
                        cgi.escape(self.__sources["right" if side else "left"].getName()),
                        cgi.escape(otherSong.text()),
                        cgi.escape(self.findChild(QComboBox, "{}Playlist".format("left" if side else "left")).currentText()),
                        cgi.escape(self.__sources["left" if side else "right"].getName())
                    ))
                    break
            if not found:
                song.setForeground(QColor(127, 0, 0))
                self.log.emit('Song <span style="color: #be0000">{}</span> from tracklist <strong>{}</strong> in <strong>{}</strong> not found in tracklist <strong>{}</strong> from <strong>{}</strong>'.format(
                    cgi.escape(song.text()),
                    cgi.escape(self.findChild(QComboBox, "{}Playlist".format("right" if side else "left")).currentText()),
                    cgi.escape(self.__sources["right" if side else "left"].getName()),
                    cgi.escape(self.findChild(QComboBox, "{}Playlist".format("left" if side else "left")).currentText()),
                    cgi.escape(self.__sources["left" if side else "right"].getName())
                ))

        # FIXME: Should only be run when both tracklists finished downloading
        self.status.emit("Finished comparing tracks.")
        self.setCompleted(True)

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
        selectedSourceLayout = QHBoxLayout()
        sourceLabel = QLabel("Selected source: None")
        sourceLabel.setObjectName(side + "SourceLabel")
        selectedSourceLayout.addWidget(sourceLabel, 1)
        changeSourceBtn = QPushButton("Change...")
        changeSourceBtn.setObjectName(side + "SourceBtn")
        changeSourceBtn.clicked.connect(lambda: self.__account_select(side))
        selectedSourceLayout.addWidget(changeSourceBtn)
        playlistLabel = QLabel("Selected playlist:")
        playlistLabel.setObjectName(side + "PlaylistLabel")
        playlistLabel.setDisabled(True)
        selectedSourceLayout.addWidget(playlistLabel)
        playlistSelect = QComboBox()
        playlistSelect.setDisabled(True)
        playlistSelect.setObjectName(side + "Playlist")
        playlistSelect.currentIndexChanged.connect(lambda: self.__playlist_select(side))
        selectedSourceLayout.addWidget(playlistSelect, 1)
        sourceLayout.addLayout(selectedSourceLayout)

        trackList = QListWidget()
        trackList.setObjectName(side + "Tracklist")
        trackList.itemClicked.connect(self.__track_select)
        sourceLayout.addWidget(trackList)
        return sourceLayout

    def __load_accounts(self):
        if (os.path.isfile(self.__accounts_file)):
            try:
                with open(self.__accounts_file, "r") as f:
                    accounts = json.load(f)
                for k,v in accounts.items():
                    self.__accounts[k] = modules.create_object(v)
                    self.__accounts[k].setId(k)
                    self.__accounts[k].initialize()
                    self.__accounts[k].status.connect(self.status.emit)
            except Exception as e:
                print("Cannot parse accounts configuration: {}".format(str(e)), file=stderr)

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

        page2 = Page2()
        self.__parent.addPage(self)
        self.__parent.addPage(page2)

    def __init__(self, parent):
        super().__init__()
        self.__parent = parent

        self.__build_ui()
        self.__load_accounts()

    def getSource(self, s):
        return self.__sources[s]

    def update(self):
        pass
