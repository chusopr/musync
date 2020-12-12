from wizard import WizardPage
from PySide2.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QListWidget, QGridLayout, QLabel, QComboBox, QSpacerItem, QSizePolicy, QFrame
from PySide2.QtCore import Qt, Signal, Slot
from PySide2.QtGui import QBrush, QColor
import threading

class Page2(WizardPage):
    __new_song_row =  Signal(int, str, list)
    __songs_table = None

    def __init__(self):
        super().__init__()
        page2Layout = QVBoxLayout(self)

        table_header = QHBoxLayout()
        lLabel = QLabel()
        lLabel.setObjectName("lLabel")
        table_header.addWidget(lLabel)
        table_header.addItem(QSpacerItem(1, 1, QSizePolicy.Expanding, QSizePolicy.Minimum))
        rLabel = QLabel()
        rLabel.setObjectName("rLabel")
        table_header.addWidget(rLabel)
        page2Layout.addLayout(table_header)

        hLine = QFrame(self.__songs_table)
        hLine.setFrameShape(QFrame.HLine)
        hLine.setFrameShadow(QFrame.Sunken)
        page2Layout.addWidget(hLine)

        scrollArea = QScrollArea()
        scrollClient = QWidget()
        scrollClient.setObjectName("scrollClient")
        scrollArea.setWidgetResizable(True)
        scrollArea.setWidget(scrollClient)
        page2Layout.addWidget(scrollArea)

        self.__new_song_row.connect(self.__add_song_row)

    @Slot(int)
    def __selected_item_changed(self, i):
        if i == 0:
            self.sender().setStyleSheet("QComboBox { border:0; } QComboBox:editable { color:rgb(127,0,0); }")
        else:
            self.sender().setStyleSheet("QComboBox { border:0; } QComboBox:editable { color:inherit; }")

    @Slot(int, str, list)
    def __add_song_row(self, side, title, search_results):
        label = QLabel(title)
        label.setToolTip(title)
        label.setSizePolicy(QSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred))
        self.__songs_table.addWidget(label, self.__songs_table.rowCount(), side)
        combo = QComboBox()
        combo.currentIndexChanged.connect(self.__selected_item_changed)
        combo.setSizePolicy(QSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed))
        combo.setStyleSheet("border:0")

        if search_results:
            combo.addItem("Don't sync", None)
            combo.setItemData(0, QBrush(QColor(127, 0, 0)), Qt.TextColorRole)
            for r in search_results:
                combo.addItem("{} - {}".format(r["artist"], r["title"]), r)
            combo.setCurrentIndex(1)
        else:
            combo.addItem("No songs found", None)
            combo.setDisabled(True)

        combo.setToolTip(combo.currentText())
        combo.currentTextChanged.connect(combo.setToolTip)

        self.__songs_table.addWidget(combo, self.__songs_table.rowCount()-1, int(not side))

    def __search_songs(self):
        lList = self.parent().findChild(QListWidget, "leftTracklist")
        rList = self.parent().findChild(QListWidget, "rightTracklist")
        lPos = rPos = 0

        sources = self.parent().parent().parent().page(0).getSources()

        lCombo = self.parent().parent().parent().findChild(QComboBox, "leftPlaylist")
        rCombo = self.parent().parent().parent().findChild(QComboBox, "rightPlaylist")
        self.findChild(QLabel, "lLabel").setText("{} in {}".format(lCombo.currentText(), sources["left"].getName()))
        self.findChild(QLabel, "lLabel").setToolTip("{} in {}".format(lCombo.currentText(), sources["left"].getName()))
        self.findChild(QLabel, "rLabel").setText("{} in {}".format(rCombo.currentText(), sources["right"].getName()))
        self.findChild(QLabel, "rLabel").setToolTip("{} in {}".format(rCombo.currentText(), sources["right"].getName()))

        # FIXME: crashes if left list is empty
        while lPos < lList.count() or rPos < rList.count():
            self.status.emit("Searching songs ({} % completed).".format(round((lPos+rPos)*100/(lList.count()+rList.count()))))
            if (lPos < rPos and lPos < lList.count()) or ((lPos >= rPos) and (rPos >= rList.count())):
                lPos = lPos + 1
                if sources["right"].isReadOnly():
                    continue
                song = lList.item(lPos-1)
                side = 0
            else:
                rPos = rPos + 1
                if sources["left"].isReadOnly():
                    continue
                song = rList.item(rPos-1)
                side = 1

            if "peer" in song.track and song.track["peer"] is not None:
                continue

            search_results = sources["left" if side else "right"].searchTrack(song.track)
            self.__new_song_row.emit(side, "{} - {}".format(song.track["artist"], song.track["title"]), search_results)

        self.status.emit("Searching songs completed.".format(int((lPos+rPos)*100/(lList.count()+rList.count()))))
        self.setCompleted(True)

    def update(self):
        scroll_client = self.findChild(QWidget, "scrollClient")
        if self.__songs_table:
            self.__songs_table.deleteLater()
            del self.__songs_table

        self.__songs_table = QGridLayout()
        self.__songs_table.setObjectName("songs_table")
        self.__songs_table.addItem(QSpacerItem(1, 1, QSizePolicy.Expanding, QSizePolicy.Expanding), 0, 0, 1, 2)

        scroll_client.setLayout(self.__songs_table)

        thread = threading.Thread(target=self.__search_songs)
        thread.start()
