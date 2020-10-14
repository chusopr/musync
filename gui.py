from PyQt5.QtWidgets import QWizard, QWizardPage, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QLabel, QComboBox, QDialog, QMessageBox, QListWidgetItem, QStatusBar, QTextBrowser, QCheckBox, QGridLayout, QScrollArea
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QColor
from datetime import datetime
import re, modules, icu, threading, cgi, json, os
from appdirs import user_config_dir
from sys import stderr

class Page1(QWizardPage):
    __completed = False

    def __init__(self):
        super().__init__()

    def update(self):
        pass

    def setCompleted(self, c):
        self.__completed = c
        self.completeChanged.emit()

    def isComplete(self):
        return self.__completed

class Page2(QWizardPage):
    __completed = False

    def __init__(self):
        super().__init__()

    def update(self):
        lList = self.parent().findChild(QListWidget, "leftTracklist")
        rList = self.parent().findChild(QListWidget, "rightTracklist")

        scroll_client = self.findChild(QWidget, "scrollClient")
        songs_table = self.findChild(QGridLayout, "songs_table")
        if songs_table:
            songs_table.deleteLater()
        songs_table = QGridLayout()
        songs_table.setObjectName("songs_table")
        scroll_client.setLayout(songs_table)

        lPos = rPos = 0
        # TODO: use a similar approach for colouring the previous page, which must be more efficient
        # FIXME: crashes if left list is empty
        while lPos < lList.count() or rPos < rList.count():
            if (lPos < rPos and lPos < lList.count()) or ((lPos >= rPos) and (rPos >= rList.count())):
                song = lList.item(lPos)
                lPos = lPos + 1
                side = 0
            else:
                song = rList.item(rPos)
                rPos = rPos + 1
                side = 1

            if "peer" in song.track and song.track["peer"]:
                continue

            songs_table.addWidget(QLabel("{} - {}".format(song.track["artist"], song.track["title"])), songs_table.rowCount(), side)
            songs_table.addWidget(QComboBox(), songs_table.rowCount()-1, int(not side))

    def setCompleted(self, c):
        self.__completed = c

    def isComplete(self):
        return self.__completed

class MainWindow(QWizard):
    __sources = {
        "left":  None,
        "right": None
    }
    __threads = {
        "left": None,
        "right": None,
        "compare": None
    }
    __accounts_file = os.path.join(user_config_dir("musync"), "accounts.json")
    __log = None
    __accounts = {}

    def __init__(self):
        super().__init__()
        self.buildUI()
        modules.load(self)
        if (os.path.isfile(self.__accounts_file)):
            try:
                with open(self.__accounts_file, "r") as f:
                    accounts = json.load(f)
                for k,v in accounts.items():
                    self.__accounts[k] = modules.create_object(self, v)
                    self.__accounts[k].setId(k)
                    self.__accounts[k].initialize()
            except Exception as e:
                print("Cannot parse accounts configuration: {}".format(str(e)), file=stderr)

    def __save_settings(self):
        s = {}
        for k,v in self.__accounts.items():
            s[k] = v.getType()
        os.makedirs(os.path.dirname(self.__accounts_file), 0o700, True)
        with open(self.__accounts_file, "w") as f:
            json.dump(s, f)

    def __bogus_module(self, module_name):
        errorMsg = QMessageBox(QMessageBox.Critical, "Bogus module", module_name + " module is not working properly", QMessageBox.Ok, self)
        errorMsg.show()

    def __compare_playlists(self):
        self.page(0).setCompleted(False)
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
                    self.__status_updated('Song <span style="color: #00be00">{}</span> from tracklist <strong>{}</strong> in <strong>{}</strong> found as <span style="color: #00be00">{}</span> in tracklist <strong>{}</strong> from <strong>{}</strong>'.format(
                        cgi.escape(l.text()),
                        cgi.escape(self.findChild(QComboBox, "leftPlaylist").currentText()),
                        cgi.escape(self.__sources["left"].getName()),
                        cgi.escape(r.text()),
                        cgi.escape(self.findChild(QComboBox, "rightPlaylist").currentText()),
                        cgi.escape(self.__sources["right"].getName())
                    ), False)
                    break
            if not found:
                l.setForeground(QColor(127, 0, 0))
                self.__status_updated('Song <span style="color: #be0000">{}</span> from tracklist <strong>{}</strong> in <strong>{}</strong> not found in tracklist <strong>{}</strong> from <strong>{}</strong>'.format(
                    cgi.escape(l.text()),
                    cgi.escape(self.findChild(QComboBox, "leftPlaylist").currentText()),
                    cgi.escape(self.__sources["left"].getName()),
                    cgi.escape(self.findChild(QComboBox, "rightPlaylist").currentText()),
                    cgi.escape(self.__sources["right"].getName())
                ), False)

        # FIXME: Should only be run when both tracklists finished downloading
        self.statusBar().showMessage("Finished comparing tracks.")
        self.page(0).setCompleted(True)

        for i in range(rList.count()):
            r = rList.item(i)
            if r.foreground() != QColor(0, 127, 0):
                r.setForeground(QColor(127, 0, 0))
                self.__status_updated('Song <span style="color: #be0000">{}</span> from tracklist <strong>{}</strong> in <strong>{}</strong> not found in tracklist <strong>{}</strong> from <strong>{}</strong>'.format(
                    cgi.escape(r.text()),
                    cgi.escape(self.findChild(QComboBox, "rightPlaylist").currentText()),
                    cgi.escape(self.__sources["right"].getName()),
                    cgi.escape(self.findChild(QComboBox, "leftPlaylist").currentText()),
                    cgi.escape(self.__sources["left"].getName())
                ), False)

    def __load_tracks(self, source_name):
        self.page(0).setCompleted(False)
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
            QListWidgetItem("{} - {}".format(t["artist"], t["title"]), trackList).track = t

        # Check if the other playlist is also set to compare both
        if self.findChild(QComboBox, "{}Playlist".format("left" if source_name == "right" else "right")).currentData() is not None:
            thread = threading.Thread(target=self.__compare_playlists)
            self.__threads["compare"] = thread
            thread.start()

    def __playlist_select(self, source_name):
        self.page(0).setCompleted(False)
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

    def __change_account(self, source_name, accountsDialog, accountsList, sourceName):
        self.page(0).setCompleted(False)
        source = accountsList.selectedItems()[0].source
        if not source.isAuthenticated() and not source.authenticate(self):
            # TODO show error
            return False

        playlists = source.getPlaylists()
        if not playlists or len(playlists) == 0:
            self.__bogus_module(source.getName())
            return
        self.findChild(QLabel, sourceName + "SourceLabel").setText("Selected source: " + source.getName())
        self.__sources[sourceName] = source
        playlistSelect = self.findChild(QComboBox, source_name + "Playlist")
        playlistSelect.clear()
        playlistSelect.addItem("")
        for playlist in playlists:
            playlistSelect.addItem(playlist["name"], playlist["id"])
        accountsDialog.close()
        playlistSelect.setDisabled(False)
        self.findChild(QLabel, source_name + "PlaylistLabel").setDisabled(False)

    def __add_account(self, sourceDialog, sourcesList, accountsList):
        module_name = sourcesList.currentItem().text()
        module_slug = sourcesList.currentItem().slug

        if not module_slug in modules.modules:
            self.__bogus_module(module_name)
            return

        source = modules.create_object(self, module_slug)

        if not source.authenticate(self):
            return False

        if source.getId() in self.__accounts.keys():
            errorMsg = QMessageBox(QMessageBox.Critical, "Account already exists", "This account already exists. Please delete it first.", QMessageBox.Ok, self)
            errorMsg.show()
            return
        self.__accounts[source.getId()] = source

        accountItem = QListWidgetItem(source.getName())
        accountItem.source = source
        accountsList.addItem(accountItem)
        sourceDialog.close()
        self.__save_settings()

    def __source_select(self, accountsList):
        sourceDialog = QDialog(self)
        sourceDialog.setWindowTitle("muSync - Sources")
        sourceDialog.setModal(True)
        dialogLayout = QVBoxLayout(sourceDialog)
        sourcesList = QListWidget()
        dialogLayout.addWidget(sourcesList)
        buttonsLayout = QHBoxLayout()
        okButton = QPushButton(QIcon.fromTheme("dialog-ok"), "&Ok")
        okButton.clicked.connect(lambda: self.__add_account(sourceDialog, sourcesList, accountsList))
        okButton.setDisabled(True)
        buttonsLayout.addWidget(okButton)
        cancelButton = QPushButton(QIcon.fromTheme("dialog-cancel"), "&Cancel")
        cancelButton.clicked.connect(sourceDialog.close)
        buttonsLayout.addWidget(cancelButton)
        dialogLayout.addLayout(buttonsLayout)
        for source in modules.modules.items():
            sourceItem = QListWidgetItem(source[1])
            sourceItem.slug = source[0]
            sourcesList.addItem(sourceItem)
        sourcesList.itemSelectionChanged.connect(lambda: okButton.setDisabled(True if sourcesList.selectedIndexes() == [] else False))
        sourcesList.itemDoubleClicked.connect(lambda: self.__add_account(sourceDialog, sourcesList, accountsList))
        sourceDialog.show()

    def __del_account (self, source_name, accountsDialog, accountsList, sourceName):
        del self.__accounts[accountsList.selectedItems()[0].source.getId()]
        accountsList.selectedItems()[0].source.deleteAccount()
        accountsList.takeItem(accountsList.currentRow())
        self.__save_settings()

    def __account_select(self, source_name):
        source_modules = modules.listAll()
        if len(source_modules) == 0:
            errorMsg = QMessageBox(QMessageBox.Critical, "No sources available", "No source modules found", QMessageBox.Ok, self)
            errorMsg.show()
            return

        sourceName = re.sub(r"SourceBtn$", "", self.sender().objectName())
        accountsDialog = QDialog(self)
        accountsDialog.setWindowTitle("muSync - Accounts")
        accountsDialog.setModal(True)
        dialogLayout = QVBoxLayout(accountsDialog)
        accountsList = QListWidget()
        dialogLayout.addWidget(accountsList)
        buttonsLayout = QHBoxLayout()
        addButton = QPushButton(QIcon.fromTheme("list-resource-add"), "&Add account")
        addButton.clicked.connect(lambda: self.__source_select(accountsList))
        buttonsLayout.addWidget(addButton)
        delButton = QPushButton(QIcon.fromTheme("edit-delete"), "&Remove account")
        delButton.clicked.connect(lambda: self.__del_account(source_name, accountsDialog, accountsList, sourceName))
        delButton.setDisabled(True)
        buttonsLayout.addWidget(delButton)
        okButton = QPushButton(QIcon.fromTheme("dialog-ok"), "&Select source")
        okButton.clicked.connect(lambda: self.__change_account(source_name, accountsDialog, accountsList, sourceName))
        okButton.setDisabled(True)
        buttonsLayout.addWidget(okButton)
        cancelButton = QPushButton(QIcon.fromTheme("dialog-cancel"), "&Cancel")
        cancelButton.clicked.connect(accountsDialog.close)
        buttonsLayout.addWidget(cancelButton)
        dialogLayout.addLayout(buttonsLayout)
        accountsList.itemSelectionChanged.connect(lambda: okButton.setDisabled(True if accountsList.selectedIndexes() == [] else False))
        accountsList.itemSelectionChanged.connect(lambda: delButton.setDisabled(True if accountsList.selectedIndexes() == [] else False))

        for account in self.__accounts.values():
            sourceItem = QListWidgetItem(account.getName())
            sourceItem.source = account
            accountsList.addItem(sourceItem)

        accountsList.itemDoubleClicked.connect(lambda: self.__change_account(source_name, accountsDialog, accountsList, sourceName))
        accountsDialog.show()

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

    def __start_sync(self):
        if not (self.sources["left"] and self.sources["right"] and self.playlists["left"] and self.playlists["right"]):
            errorMsg = QMessageBox(QMessageBox.Warning, "No sources selected", "You must select sources and playlists first", QMessageBox.Ok, self)
            errorMsg.show()
            return
        errorMsg = QMessageBox(QMessageBox.Warning, "No sources selected", "OK first", QMessageBox.Ok, self)
        errorMsg.show()

    def __status_updated(self, msg, escape=True):
        if self.__log is not None:
            log = self.__log.findChild(QTextBrowser, "log")
            log.append('<span style="color: #bebebe">{} - </span>{}'.format(datetime.now(), cgi.escape(msg) if escape else msg))
            if self.__log.findChild(QCheckBox, "autoscroll").isChecked():
                log.verticalScrollBar().setValue(log.verticalScrollBar().maximum())

    def __copy_log(self):
        self.__log.findChild(QTextBrowser, "log").selectAll()
        self.__log.findChild(QTextBrowser, "log").copy()

    def __add_song(self, tracksDialog, searchTracksList, sourceTrack, sourceTrackList, destination):
        trackResult = searchTracksList.currentItem()
        destTrackList = self.findChild(QListWidget, "{}Tracklist".format(destination))

        sourceTrack.setForeground(QColor(127, 127, 0))
        destTrack = QListWidgetItem("{} - {}".format(trackResult.track["artist"], trackResult.track["title"]), destTrackList)
        destTrack.track = trackResult.track
        destTrack.track["peer"] = sourceTrackList.row(sourceTrack)
        sourceTrack.track["peer"] = destTrackList.row(destTrack)
        destTrack.setForeground(QColor(127, 127, 0))
        sourceTrack.peer = destTrack

        self.__status_updated('Song <span style="color: #00be00">{}</span> queued to be added to tracklist <strong>{}</strong> in <strong>{}</strong>'.format(
            cgi.escape(destTrack.text()),
            cgi.escape(self.findChild(QComboBox, "{}Playlist".format(destination)).currentText()),
            cgi.escape(self.__sources[destination].getName())
        ), False)
        tracksDialog.close()

    def __search_song(self, source, destination):
        sTrackList = self.findChild(QListWidget, "{}Tracklist".format(source))
        t = sTrackList.selectedItems()[0]
        search_results = self.__sources[destination].searchTrack(t.track)

        tracksDialog = QDialog(self)
        tracksDialog.setWindowTitle("muSync - {} - {}".format(t.track["artist"], t.track["title"]))
        tracksDialog.setModal(True)
        tracksLayout = QVBoxLayout(tracksDialog)
        tracksList = QListWidget()
        tracksLayout.addWidget(tracksList)
        buttonsLayout = QHBoxLayout()
        selectButton = QPushButton(QIcon.fromTheme("dialog-ok"), "&Select")
        selectButton.clicked.connect(lambda: self.__add_song(tracksDialog, tracksList, t, sTrackList, destination))
        selectButton.setDisabled(True)
        buttonsLayout.addWidget(selectButton)
        cancelButton = QPushButton(QIcon.fromTheme("dialog-cancel"), "&Cancel")
        cancelButton.clicked.connect(tracksDialog.close)
        buttonsLayout.addWidget(cancelButton)
        tracksLayout.addLayout(buttonsLayout)
        for r in search_results:
            trackItem = QListWidgetItem("{} - {}".format(r["artist"], r["title"]))
            trackItem.track = r
            tracksList.addItem(trackItem)
        tracksList.itemSelectionChanged.connect(lambda: selectButton.setDisabled(True if tracksList.selectedIndexes() == [] else False))
        tracksList.itemDoubleClicked.connect(lambda: self.__add_song(tracksDialog, tracksList, t, sTrackList, destination))
        tracksDialog.show()

    def statusBar(self):
        return self.findChild(QStatusBar, "statusBar")

    def __page_changed(self):
        if self.currentPage() is not None:
            self.currentPage().children()[0].addWidget(self.statusBar())
            self.currentPage().update()

    def buildUI(self):
        page1 = Page1()
        page1Layout = QVBoxLayout(page1)

        sourcesLayout = QHBoxLayout()
        page1Layout.addLayout(sourcesLayout)

        leftLayout, leftPlaylist, leftTracklist, leftSourceBtn = self.__create_source_layout("left")
        sourcesLayout.addLayout(leftLayout)
        rightLayout, rightPlaylist, rightTracklist, rightSourceBtn = self.__create_source_layout("right")
        sourcesLayout.addLayout(rightLayout)

        statusBar = QStatusBar(self)
        statusBar.setObjectName("statusBar")
        statusBar.messageChanged.connect(self.__status_updated)

        page1Layout.addWidget(statusBar)
        self.addPage(page1)

        page2 = Page2()
        page2Layout = QVBoxLayout(page2)
        scrollArea = QScrollArea()
        scrollClient = QWidget()
        scrollClient.setObjectName("scrollClient")
        scrollArea.setWidgetResizable(True)
        scrollArea.setWidget(scrollClient)
        page2Layout.addWidget(scrollArea)
        self.addPage(page2)

        self.__log = QDialog(self)
        self.__log.resize(540, 250)
        self.__log.setModal(False)
        logLayout = QVBoxLayout(self.__log)
        logBrowser = QTextBrowser()
        logBrowser.setObjectName("log")
        logBrowser.setAcceptRichText(True)
        logBrowser.setReadOnly(True)
        logLayout.addWidget(logBrowser)
        buttonsLayout = QHBoxLayout()
        autoScroll = QCheckBox("Auto-scroll")
        autoScroll.setObjectName("autoscroll")
        autoScroll.setChecked(True)
        buttonsLayout.addWidget(autoScroll)
        clearButton = QPushButton(QIcon.fromTheme("delete"), "C&lear")
        clearButton.clicked.connect(logBrowser.clear)
        buttonsLayout.addWidget(clearButton)
        copyButton = QPushButton(QIcon.fromTheme("edit-copy"), "Co&py")
        copyButton.clicked.connect(self.__copy_log)
        buttonsLayout.addWidget(copyButton)
        closeButton = QPushButton(QIcon.fromTheme("dialog-close"), "&Close")
        closeButton.clicked.connect(self.__log.close)
        buttonsLayout.addWidget(closeButton)
        logLayout.addLayout(buttonsLayout)

        self.setButtonText(QWizard.CustomButton1, "&Logs")
        self.setOption(QWizard.HaveCustomButton1, True)
        self.customButtonClicked.connect(self.__log.show)

        self.currentIdChanged.connect(self.__page_changed)

        # Show window
        self.setWindowTitle('muSync')
        self.show()
