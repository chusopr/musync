from wizard import WizardPage
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QListWidget, QGridLayout, QLabel, QComboBox
from PyQt5.QtCore import pyqtSignal
import threading

class Page2(WizardPage):
    __new_song_row =  pyqtSignal(int, str, list)
    __songs_table = None

    def __init__(self):
        super().__init__()
        page2Layout = QVBoxLayout(self)
        scrollArea = QScrollArea()
        scrollClient = QWidget()
        scrollClient.setObjectName("scrollClient")
        scrollArea.setWidgetResizable(True)
        scrollArea.setWidget(scrollClient)
        page2Layout.addWidget(scrollArea)
        self.__new_song_row.connect(self.__add_song_row)

    def __add_song_row(self, side, label, search_results):
        self.__songs_table.addWidget(QLabel(label), self.__songs_table.rowCount(), side)
        combo = QComboBox()
        combo.setStyleSheet("border:0")

        if search_results:
            for r in search_results:
                combo.addItem("{} - {}".format(r["artist"], r["title"]), r["id"])
        else:
            combo.addItem("No songs found", None)

        self.__songs_table.addWidget(combo, self.__songs_table.rowCount()-1, int(not side))

    def __search_songs(self, songs_table):
        lList = self.parent().findChild(QListWidget, "leftTracklist")
        rList = self.parent().findChild(QListWidget, "rightTracklist")
        lPos = rPos = 0

        sources = {
            "left": self.parent().parent().parent().page(0).getSource("left"),
            "right": self.parent().parent().parent().page(0).getSource("right")
        }

        # FIXME: crashes if left list is empty
        while lPos < lList.count() or rPos < rList.count():
            self.status.emit("Searching songs ({} % completed).".format(int((lPos+rPos)*100/(lList.count()+rList.count()))))
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

            if "peer" in song.track and song.track["peer"]:
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
        scroll_client.setLayout(self.__songs_table)

        thread = threading.Thread(target=self.__search_songs, args=(self.__songs_table,))
        thread.start()
