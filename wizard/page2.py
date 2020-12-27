from wizard import WizardPage
from PySide2.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QListWidget, QGridLayout, QLabel, QComboBox, QSpacerItem, QSizePolicy, QFrame
from PySide2.QtCore import Qt, Signal, Slot
from PySide2.QtGui import QBrush, QColor
import threading


class Page2(WizardPage):
    __new_song_row = Signal(int, int, str, list)
    __songs_table = None
    __items = [{}, {}]

    def __init__(self):
        super().__init__()
        page2Layout = QVBoxLayout(self)

        table_header = QHBoxLayout()
        label0 = QLabel()
        label0.setObjectName("label0")
        table_header.addWidget(label0)
        table_header.addItem(QSpacerItem(1, 1, QSizePolicy.Expanding, QSizePolicy.Minimum))
        label1 = QLabel()
        label1.setObjectName("label1")
        table_header.addWidget(label1)
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

    def getItems(self):
        return self.__items

    @Slot(int)
    def __selected_item_changed(self, side, pos, combo):
        self.__items[side]["tracks"][pos]["dst"] = combo.currentData()
        if combo.currentData() is None:
            combo.setStyleSheet("QComboBox { border:0; } QComboBox:editable { color:rgb(127,0,0); }")
        else:
            combo.setStyleSheet("QComboBox { border:0; } QComboBox:editable { color:inherit; }")

    @Slot(int, int, str, list)
    def __add_song_row(self, side, pos, title, search_results):
        label = QLabel(title)
        label.setToolTip(title)
        label.setSizePolicy(QSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred))
        self.__songs_table.addWidget(label, self.__songs_table.rowCount(), side)
        combo = QComboBox()
        combo.currentIndexChanged.connect(lambda i: self.__selected_item_changed(int(not side), pos, combo))
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

        self.__songs_table.addWidget(combo, self.__songs_table.rowCount() - 1, int(not side))

    def getItems(self):
        return self.__items

    def __search_songs(self, sources, playlist0, playlist1, items):
        pos0 = pos1 = 0

        self.__items = {0: {"playlist": playlist0, "tracks": {}}, 1: {"playlist": playlist1, "tracks": {}}}

        # FIXME: crashes if left list is empty
        while pos0 < len(items[0]) or pos1 < len(items[1]):
            self.status.emit("Searching songs ({} % completed).".format(round((pos0 + pos1) * 100 / (len(items[0]) + len(items[1])))))

            if (pos0 < pos1 and pos0 < len(items[0])) or ((pos0 >= pos1) and (pos1 >= len(items[1]))):
                pos = pos0
                pos0 += 1
                side = 0
            else:
                pos = pos1
                pos1 += 1
                side = 1

            if sources[int(not side)].isReadOnly():
                continue

            song = items[side][pos]

            if "peer" in song and song["peer"] is not None:
                continue

            search_results = sources[int(not side)].searchTrack(song)
            self.__new_song_row.emit(side, pos, "{} - {}".format(song["artist"], song["title"]), search_results)
            self.__items[int(not side)]["tracks"][pos] = {"src": song, "dst": None}

        self.status.emit("Searching songs completed.".format(int((pos0 + pos1) * 100 / (len(items[0]) + len(items[1])))))
        self.setCompleted(True)

    def update(self):
        scroll_client = self.findChild(QWidget, "scrollClient")
        if self.__songs_table:
            self.__songs_table.deleteLater()
            del self.__songs_table

        sources = self.parent().parent().parent().page(0).getSources()
        items = self.parent().parent().parent().page(0).getItems()

        combo0 = self.parent().parent().parent().findChild(QComboBox, "Playlist0")
        label0 = self.findChild(QLabel, "label0")
        label0.setText("{} in {}".format(combo0.currentText(), sources[0].getName()))
        label0.setToolTip("{} in {}".format(combo0.currentText(), sources[0].getName()))
        combo1 = self.parent().parent().parent().findChild(QComboBox, "Playlist1")
        label1 = self.findChild(QLabel, "label1")
        label1.setText("{} in {}".format(combo1.currentText(), sources[1].getName()))
        label1.setToolTip("{} in {}".format(combo1.currentText(), sources[1].getName()))

        self.__songs_table = QGridLayout()
        self.__songs_table.setObjectName("songs_table")
        self.__songs_table.addItem(QSpacerItem(1, 1, QSizePolicy.Expanding, QSizePolicy.Expanding), 0, 0, 1, 2)

        scroll_client.setLayout(self.__songs_table)

        threading.Thread(target=self.__search_songs, args=(sources, combo0.currentData(), combo1.currentData(), items,)).start()
