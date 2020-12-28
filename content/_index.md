+++
title = "muSync"
description = "Synchronizing playlists across music services"
+++

{{< lead >}}musync connects to your accounts in different music services to synchronize playlists.{{< /lead >}}

It can be used, for example, for synchronizing your favourites between different accounts and services or copying playlists.

## Introduction

It works as a wizard in three steps:

1. You configure two playlists in the same or different music service accounts and the software finds and highlights songs that are present in only one of the playlists.  
2. In the second step, for every song that is present in only one playlist, the software searches for a corresponding song in the other service that can be added to the playlist where it's missing and the user is asked to confirm the results are correct or to choose an alternative form any of the search results.  
3. Finally, the results are written and all the songs the user choose to synchronize are added to the playlists.

More details about muSync use can be found in the [user guide]({{< relref "/user-guide" >}}).

## Screenshots

{{< figure src="page1.png" link="page1.png" alt="muSync first step" width="620" >}}
{{< figure src="page2.png" link="page2.png" alt="muSync second step" width="620" >}}

## Requirements

It requires Python 3.8 or later and the following dependencies:

* PySide2
* python3-icu (optional, but recommended)
* python3-requests
* python3-selenium
* chromedriver

## Development status

This software is currently under heavy development and the versions currently available are still in [alpha stage](https://en.wikipedia.org/wiki/Software_release_life_cycle#Alpha) with some bugs and many limitations.

### Limitations

* ~~Chromedriver path is hardcoed to `/usr/bin/chromedriver`. If the path in your system is different, you will have to change it in `musync/modules/amazon/__init__.py` and `musync/modules/lastfm/__init__.py`.~~  
Fixed in [`f78e3fc7`](https://github.com/chusopr/musync/commit/f78e3fc7).
* ~~Sensitive data like auth tokens is stored in plaintext files in the user's home directory. That must change to store them securely, probably via [keyring](https://github.com/jaraco/keyring).~~  
Fixed in [`71c9fe25`](https://github.com/chusopr/musync/commit/f78e3fc7) and [`112cb5fa`](https://github.com/chusopr/musync/commit/112cb5fa)
* For now, only copying from Amazon Music to Last.fm loved tracks is suppported. More to be implemented.
* Going back in the wizard is not tested and would have unpredictable results. Hence, the _Back_ button was made unavailable until the ability to go back without making a mess is implemented.
* If you don't want to sync a song, it will be asked again the next time you run the sync. These decisions need to be remembered.
* Threads support is not finished. Downloading playslists, comparing them and syncing them is done in separate threads so the main thread is not blocked and it nicely show progress to the user, but closing the application while some thread is running won't stop the thread, it will onyl close the UI and keep the thread ruinning in the background until it finishes.

### Bugs

* ~~For some weird reason, adding a new account usually don't work the first time and you have to do it twice.~~  
Seems to be gone.
* ~~If you try to add the second source before the first one starts syncing, the dialog box to select the second source will be closed when the first source starts syncing, for some uknown weird reason, and you will have to try adding the source again.~~  
Seems to be gone.
* ~~If one playlist is empty in the first step, the second step will crash.~~  
Fixed in [`5cca7b6a`](https://github.com/chusopr/musync/commit/5cca7b6a).

### Roadmap

* Obviously, fix the bugs and limitations above.
* Add support for Spotify and YouTube.
* Add support for syncing recently played songs.
* Add support for other browsers than Chrome (namely, Firefox).
* Add support for creating playlists. At this moment, it only allows syncing to already-existing playlists.

{{< clearfix >}}
