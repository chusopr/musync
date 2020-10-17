from wizard import WizardPage
from PyQt5.QtWidgets import QWidget, QListWidget, QGridLayout, QLabel, QComboBox

class Page2(WizardPage):
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
        sources = {
            "left": self.parent().parent().parent().getSource("left"),
            "right": self.parent().parent().parent().getSource("right")
        }
        # TODO: use a similar approach for colouring the previous page, which must be more efficient
        # FIXME: crashes if left list is empty
        while lPos < lList.count() or rPos < rList.count():
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

            songs_table.addWidget(QLabel("{} - {}".format(song.track["artist"], song.track["title"])), songs_table.rowCount(), side)

            combo = QComboBox()
            combo.setStyleSheet("border:0")

            search_results = sources["left" if side else "right"].searchTrack(song.track)
            if search_results:
                for r in search_results:
                    combo.addItem("{} - {}".format(r["artist"], r["title"]), r["id"])
            else:
                combo.addItem("No songs found", None)

            songs_table.addWidget(combo, songs_table.rowCount()-1, int(not side))
