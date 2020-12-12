from wizard import WizardPage

from PySide2.QtWidgets import QWizard, QWidget, QVBoxLayout, QLabel, QComboBox, QScrollArea, QGridLayout, QSpacerItem, QSizePolicy
from PySide2.QtGui import QIcon
from PySide2.QtCore import QRect, Signal, Slot
import threading


class _QLabel(QLabel):
    resized = Signal()

    def resizeEvent(self, _):
        self.resized.emit()


class Page3(WizardPage):
    __song_processed = Signal(str, str, bool, bool)
    __results_table = None
    __icon_height = None

    @Slot()
    def __add_icon(self, sender, found, result):
        # Get position of the received signal
        r, _, _, _ = self.__results_table.getItemPosition(self.__results_table.indexOf(sender))
        # We are always getting the size from the first label because getting it from the sender does weird things
        if self.__icon_height is None:
            self.__icon_height = self.__results_table.itemAtPosition(1, 1).widget().height()

        # Was the icon already added?
        iconLabel = self.__results_table.itemAtPosition(r, 0)
        if iconLabel is not None:
            # Then just resize de existing one
            iconLabel.setGeometry(QRect(0, 0, self.__icon_height, self.__icon_height))
        else:
            # Otherwise, add it
            icon = QIcon.fromTheme("{}".format("dialog-cancel" if not found else "dialog-ok" if result else "dialog-close"))
            iconLabel = QLabel()
            iconLabel.setPixmap(icon.pixmap(self.__icon_height, self.__icon_height))
            self.__results_table.addWidget(iconLabel, r, 0)

    @Slot(str, str, bool, bool)
    def __add_song_results(self, title, dest, found, result):
        titleLabel = _QLabel(title)
        # The icon needs to be added after the correct size of the label is set
        self.__results_table.addWidget(titleLabel, self.__results_table.rowCount(), 1)
        titleLabel.resized.connect(lambda: self.__add_icon(titleLabel, found, result))
        self.__results_table.addWidget(QLabel(dest), self.__results_table.rowCount() - 1, 2)

    def __sync_songs(self):
        lLabel = self.parent().findChild(QLabel, "lLabel")
        rLabel = self.parent().findChild(QLabel, "rLabel")
        songs_table = self.parent().findChild(QGridLayout, "songs_table")
        sources = self.parent().parent().parent().page(0).getSources()
        lPlaylist = self.parent().parent().parent().findChild(QComboBox, "leftPlaylist").currentData()
        rPlaylist = self.parent().parent().parent().findChild(QComboBox, "rightPlaylist").currentData()

        for i in range(1, songs_table.rowCount()):
            self.status.emit("Syncing songs ({} % completed).".format(round((i - 1) * 100 / (songs_table.rowCount() - 1))))
            leftItem = songs_table.itemAtPosition(i, 0).widget()
            rightItem = songs_table.itemAtPosition(i, 1).widget()

            src = leftItem.text() if type(leftItem) is QLabel else rightItem.text()
            dst = rightItem if type(leftItem) is QLabel else leftItem
            dstLabel = lLabel.text() if type(leftItem) is QLabel else rLabel.text()

            if dst.currentData() is None:
                self.__song_processed.emit(src, dstLabel, False, False)
            else:
                self.__song_processed.emit(src, dstLabel, True, sources["right" if type(leftItem) is QLabel else "left"].addTrack(rPlaylist if type(leftItem) is QLabel else lPlaylist, dst.currentData()))

            for w in [leftItem, rightItem]:
                songs_table.removeWidget(w)
                w.deleteLater()

        self.status.emit("Finished syncing songs")
        self.setCompleted(True)
        self.parent().parent().parent().setButtonLayout([QWizard.Stretch, QWizard.CustomButton1, QWizard.NextButton, QWizard.FinishButton])

    def update(self):
        scroll_client = self.findChild(QWidget, "scrollClient")
        if self.__results_table:
            self.__results_table.deleteLater()
            del self.__results_table

        self.__results_table = QGridLayout()
        self.__results_table.addItem(QSpacerItem(1, 1, QSizePolicy.Expanding, QSizePolicy.Expanding), 0, 0, 1, 2)

        scroll_client.setLayout(self.__results_table)

        thread = threading.Thread(target=self.__sync_songs)
        thread.start()

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
