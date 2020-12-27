from wizard import WizardPage

from PySide2.QtWidgets import QWizard, QWidget, QVBoxLayout, QLabel, QComboBox, QScrollArea, QGridLayout, QSpacerItem, QSizePolicy
from PySide2.QtGui import QIcon
from PySide2.QtCore import QRect, Signal, Slot
import threading


class Page3(WizardPage):
    __song_processed = Signal(int, dict, bool, bool)
    __results_table = None
    __icon_height = None
    __sources = {}

    @Slot(int, str, bool, bool)
    def __add_song_results(self, src, track, found, result):
        self.__results_table.addWidget(QLabel("❒" if not found else "✔" if result else "✖"), self.__results_table.rowCount(), 0)
        self.__results_table.addWidget(QLabel("{} - {}".format(track["artist"], track["title"])), self.__results_table.rowCount() - 1, 1)
        self.__results_table.addWidget(QLabel(self.__sources[src].getName()), self.__results_table.rowCount() - 1, 2)

    def __sync_songs(self, sync_list):
        playlist0 = self.parent().parent().parent().findChild(QComboBox, "Playlist0").currentData()
        playlist1 = self.parent().parent().parent().findChild(QComboBox, "Playlist1").currentData()

        total = sum(len(x[1].items()) for x in sync_list.items())

        count = 0
        for src, items in sync_list.items():
            for _, track in items["tracks"].items():
                count += 1
                self.status.emit("Syncing songs ({} % completed).".format(round(count * 100 / total)))

                if track["dst"] is None:
                    self.__song_processed.emit(src, track["src"], False, False)
                else:
                    self.__song_processed.emit(src, track["dst"], True, self.__sources[src].addTrack(playlist1 if src else playlist0, track["dst"]))

        self.status.emit("Finished syncing songs")
        self.setCompleted(True)
        self.parent().parent().parent().setButtonLayout([QWizard.Stretch, QWizard.CustomButton1, QWizard.NextButton, QWizard.FinishButton])

    def update(self):
        self.__sources = self.parent().parent().parent().page(0).getSources()
        scroll_client = self.findChild(QWidget, "scrollClient")
        if self.__results_table:
            self.__results_table.deleteLater()
            del self.__results_table

        self.__results_table = QGridLayout()
        self.__results_table.addItem(QSpacerItem(1, 1, QSizePolicy.Expanding, QSizePolicy.Expanding), 0, 0, 1, 2)

        scroll_client.setLayout(self.__results_table)

        threading.Thread(target=self.__sync_songs, args=(self.parent().parent().parent().page(1).getItems(),)).start()

    def __init__(self):
        super().__init__()
        page3Layout = QVBoxLayout(self)

        scrollArea = QScrollArea()
        scrollClient = QWidget()
        scrollClient.setObjectName("scrollClient")
        scrollArea.setWidgetResizable(True)
        scrollArea.setWidget(scrollClient)
        page3Layout.addWidget(scrollArea)

        self.__song_processed.connect(self.__add_song_results)
