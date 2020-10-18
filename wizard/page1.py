from wizard import WizardPage
from wizard.page2 import Page2

from PyQt5.QtWidgets import QWizard, QVBoxLayout, QHBoxLayout, QStatusBar, QLabel, QPushButton, QComboBox, QListWidget

class Page1(WizardPage):
    __parent = None

    def __create_source_layout(self, source_name):
        sourceLayout = QVBoxLayout()
        selectedSourceLayout = QHBoxLayout()
        sourceLabel = QLabel("Selected source: None")
        sourceLabel.setObjectName(source_name + "SourceLabel")
        selectedSourceLayout.addWidget(sourceLabel, 1)
        changeSourceBtn = QPushButton("Change...")
        changeSourceBtn.setObjectName(source_name + "SourceBtn")
        changeSourceBtn.clicked.connect(lambda: self.__parent._account_select(source_name))
        selectedSourceLayout.addWidget(changeSourceBtn)
        playlistLabel = QLabel("Selected playlist:")
        playlistLabel.setObjectName(source_name + "PlaylistLabel")
        playlistLabel.setDisabled(True)
        selectedSourceLayout.addWidget(playlistLabel)
        playlistSelect = QComboBox()
        playlistSelect.setDisabled(True)
        playlistSelect.setObjectName(source_name + "Playlist")
        playlistSelect.currentIndexChanged.connect(lambda: self.__parent._playlist_select(source_name))
        selectedSourceLayout.addWidget(playlistSelect, 1)
        sourceLayout.addLayout(selectedSourceLayout)

        trackList = QListWidget()
        trackList.setObjectName(source_name + "Tracklist")
        trackList.itemClicked.connect(self.__parent._track_select)
        sourceLayout.addWidget(trackList)
        return (sourceLayout, playlistSelect, trackList, changeSourceBtn)

    def __init__(self, parent):
        super().__init__()
        self.__parent = parent

        page1Layout = QVBoxLayout(self)

        sourcesLayout = QHBoxLayout()
        page1Layout.addLayout(sourcesLayout)

        leftLayout, leftPlaylist, leftTracklist, leftSourceBtn = self.__create_source_layout("left")
        sourcesLayout.addLayout(leftLayout)
        rightLayout, rightPlaylist, rightTracklist, rightSourceBtn = self.__create_source_layout("right")
        sourcesLayout.addLayout(rightLayout)

        statusBar = QStatusBar(self)
        statusBar.setObjectName("statusBar")
        statusBar.messageChanged.connect(parent._status_updated)

        page1Layout.addWidget(statusBar)

        page2 = Page2()
        parent.addPage(self)
        parent.addPage(page2)

    def update(self):
        pass
