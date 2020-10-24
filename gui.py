from PyQt5.QtWidgets import QWizard, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QLabel, QComboBox, QDialog, QMessageBox, QListWidgetItem, QStatusBar, QTextBrowser, QCheckBox, QScrollArea
from PyQt5.QtGui import QIcon, QColor
from datetime import datetime
import re, modules, icu, threading, cgi, json, os
from wizard.page1 import Page1
from appdirs import user_config_dir
from sys import stderr

class MainWindow(QWizard):
    _sources = {
        "left":  None,
        "right": None
    }
    __accounts_file = os.path.join(user_config_dir("musync"), "accounts.json")
    __log = None
    _accounts = {}

    def __init__(self):
        super().__init__()
        self.buildUI()
        modules.load(self)
        if (os.path.isfile(self.__accounts_file)):
            try:
                with open(self.__accounts_file, "r") as f:
                    accounts = json.load(f)
                for k,v in accounts.items():
                    self._accounts[k] = modules.create_object(self, v)
                    self._accounts[k].setId(k)
                    self._accounts[k].initialize()
            except Exception as e:
                print("Cannot parse accounts configuration: {}".format(str(e)), file=stderr)

    def getSource(self, s):
        return self._sources[s]

    def _save_settings(self):
        s = {}
        for k,v in self._accounts.items():
            s[k] = v.getType()
        os.makedirs(os.path.dirname(self.__accounts_file), 0o700, True)
        with open(self.__accounts_file, "w") as f:
            json.dump(s, f)

    def _bogus_module(self, module_name):
        errorMsg = QMessageBox(QMessageBox.Critical, "Bogus module", module_name + " module is not working properly", QMessageBox.Ok, self)
        errorMsg.show()

    def _compare_playlists(self):
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
                    self._status_updated('Song <span style="color: #00be00">{}</span> from tracklist <strong>{}</strong> in <strong>{}</strong> found as <span style="color: #00be00">{}</span> in tracklist <strong>{}</strong> from <strong>{}</strong>'.format(
                        cgi.escape(l.text()),
                        cgi.escape(self.findChild(QComboBox, "leftPlaylist").currentText()),
                        cgi.escape(self._sources["left"].getName()),
                        cgi.escape(r.text()),
                        cgi.escape(self.findChild(QComboBox, "rightPlaylist").currentText()),
                        cgi.escape(self._sources["right"].getName())
                    ), False)
                    break
            if not found:
                l.setForeground(QColor(127, 0, 0))
                self._status_updated('Song <span style="color: #be0000">{}</span> from tracklist <strong>{}</strong> in <strong>{}</strong> not found in tracklist <strong>{}</strong> from <strong>{}</strong>'.format(
                    cgi.escape(l.text()),
                    cgi.escape(self.findChild(QComboBox, "leftPlaylist").currentText()),
                    cgi.escape(self._sources["left"].getName()),
                    cgi.escape(self.findChild(QComboBox, "rightPlaylist").currentText()),
                    cgi.escape(self._sources["right"].getName())
                ), False)

        # FIXME: Should only be run when both tracklists finished downloading
        self.statusBar().showMessage("Finished comparing tracks.")
        self.page(0).setCompleted(True)

        for i in range(rList.count()):
            r = rList.item(i)
            if r.foreground() != QColor(0, 127, 0):
                r.setForeground(QColor(127, 0, 0))
                self._status_updated('Song <span style="color: #be0000">{}</span> from tracklist <strong>{}</strong> in <strong>{}</strong> not found in tracklist <strong>{}</strong> from <strong>{}</strong>'.format(
                    cgi.escape(r.text()),
                    cgi.escape(self.findChild(QComboBox, "rightPlaylist").currentText()),
                    cgi.escape(self._sources["right"].getName()),
                    cgi.escape(self.findChild(QComboBox, "leftPlaylist").currentText()),
                    cgi.escape(self._sources["left"].getName())
                ), False)

    def _change_account(self, source_name, accountsList):
        self.page(0).setCompleted(False)
        source = accountsList.selectedItems()[0].source
        if not source.isAuthenticated() and not source.authenticate(self):
            # TODO show error
            return False

        playlists = source.getPlaylists()
        if not playlists or len(playlists) == 0:
            self._bogus_module(source.getName())
            return
        self.findChild(QLabel, source_name + "SourceLabel").setText("Selected source: " + source.getName())
        self._sources[source_name] = source
        playlistSelect = self.findChild(QComboBox, source_name + "Playlist")
        playlistSelect.clear()
        playlistSelect.addItem("")
        for playlist in playlists:
            playlistSelect.addItem(playlist["name"], playlist["id"])
        playlistSelect.setDisabled(False)
        self.findChild(QLabel, source_name + "PlaylistLabel").setDisabled(False)

    def __start_sync(self):
        if not (self.sources["left"] and self.sources["right"] and self.playlists["left"] and self.playlists["right"]):
            errorMsg = QMessageBox(QMessageBox.Warning, "No sources selected", "You must select sources and playlists first", QMessageBox.Ok, self)
            errorMsg.show()
            return
        errorMsg = QMessageBox(QMessageBox.Warning, "No sources selected", "OK first", QMessageBox.Ok, self)
        errorMsg.show()

    def _status_updated(self, msg, escape=True):
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

        self._status_updated('Song <span style="color: #00be00">{}</span> queued to be added to tracklist <strong>{}</strong> in <strong>{}</strong>'.format(
            cgi.escape(destTrack.text()),
            cgi.escape(self.findChild(QComboBox, "{}Playlist".format(destination)).currentText()),
            cgi.escape(self._sources[destination].getName())
        ), False)
        tracksDialog.close()

    def __search_song(self, source, destination):
        sTrackList = self.findChild(QListWidget, "{}Tracklist".format(source))
        t = sTrackList.selectedItems()[0]
        search_results = self._sources[destination].searchTrack(t.track)

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
        Page1(self)

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
