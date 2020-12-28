+++
title = "Source modules development"
+++
A muSync source module basically fullfils the following tasks:

* Returns a list of available playlists.
* Returns the list of tracks in a playlist.
* Optionally, allows adding tracks to a playlist. The module instance must be declared as read-only if this is not supported.

Modules' entry point is the `__init__.py` file in a directory with the module's name under the `modules` directory:

```
modules
├── __init__.py
├── amazon
│   └── __init__.py
└── lastfm
    └── __init__.py
```

## Interface

The module must implement the `modules.SourceModule` interface:

```python
class SourceModule(modules.SourceModule)
```

muSync modules are not allowed to import Python modules other than Python internal ones. E.g., they can import `json`, `re` or `sys`, but they shouldn't import third-party external modules like `requests` or `PySide2`.

The reason for that is that muSync modules are loaded dynamically, which makes it difficult to load external Python modules in compiled binary releases, mainly used for Windows and MacOS releases.

However, muSync's `modules` interface provides an interface to the following external modules:

### `QObject`

The `modules` package exposes Qt's `QObject` class, which allows creating Qt objects in musync modules:

```python
from modules import QObject

my_object = QObject()
```

### `MessageBox`

Class alias for Qt's `QMessageBox`. You can instanciate it to display message windows to the user.

Example:

```python
from modules import MessageBox

MessageBox(MessageBox.Information, "Example message", "This is an example message", modules.MessageBox.Ok).show()
```

See QtWidget's [C++ documentation for QMessageBox](https://doc.qt.io/qt-5/qmessagebox.html) for more details.

### `requests`

The `requests` module is available from the `modules` package allowing to send HTTP requests and receive a response:

```python
from modules import requests

playlist_request = .requests.get("http://example.com/playlist.json")

if playlist_request.status_code == 200:
    playlist = playlist_request.json()
```

See [`requests` documentation](https://requests.readthedocs.io/) for more details.

### `keyring`

The `keyring` module is available from the `modules` package allowing to store and recover credentials securely using whatever method is provided by the OS for storing credentials (OS dependent):

```python
from modules import keyring

keyring.set_password("musync", "my_module", "secret")

my_password = modules.keyring.get_password("musync", "my_module")
```

See [`keyring` documentation](https://github.com/jaraco/keyring) for usage details.

### `WebDriver`

The `modules` package includes a `WebDriver` class which extends Selenium's webdriver class by making its initialization easier and adding the following method:

#### `WebDriver.wait(self, wait_class)`

Receives a class as a parameter whose `__call__` method is called with the `WebDriver` instance as a parameter.  
The application progress is stopped until the `__call__` method returns `True`.

Example:

```python
from modules import WebDriver

class count_wait(object):
    def __call__(self, driver):
        return driver.execute_script('return document.getElementById("counter-down").textContent' = 0);

driver = WebDriver()

driver.get("https://tombruijn.github.io/counter.js/")
print('Waiting for counter to finish. Please click "Start counting!" in the website")
driver.wait(count_wait)
print("Counting finished!")
driver.quit()
```

### `WebExceptions`

Exceptions that can be thrown by the [`WebDriver`](#webdriver) class are available as `WebExceptions` in the `modules` package.

Example:

```python
from modules import WebExceptions

def get_api_table(self, driver):
    try:
        return driver.find_element_by_class_name("auth-dropdown-menu-item")
    except WebExceptions.NoSuchElementException:
        return False
```

Check the [documentation on Selenium exceptions](https://selenium-python.readthedocs.io/api.html#module-selenium.common.exceptions) for more details.

### `Signal` and `Slot`

Allows implementing Qt signals and slots in musync modules:

```python
from modules import Signal

class my_class:
    my_signal: Signal(str)

    def my_method(self):
        self.my_signal.emit("message")

    @Slot(str)
    def my_slot(self, s):
        print("Received signal with parameter {}".format(s))

    def __init__(self):
        self.my_signal.connect(self.my_slot)
	self.my_method()
```

For more details, check Qt's [C++ documentation for signals and slots](https://doc.qt.io/qt-5/signalsandslots.html).

## Attributes

### `__id`

The module's `__id` attribute must be set to a unique identifier for each module instance.

Module instances for different accounts must have different `__id`.

For example, a Last.fm module instance for user `johndoe` will have `__id = 'lastfm-johndoe` and another instance of the same module for user `janesmith` will have `__id = 'lastfm-janesmith'`.

This is also used for recoverying the account's settings when restarting the application and also by some modules to know how to initialize their instances of different accounts.

### `__authenticated`

Initially set to `False`, it must be changed to `True` only after a user is successfully signed in.

If the user authentication is no longer valid, its value must be changed back to `False` until it's again authenticated.

### `__read_only`

Initially set to `False`, it must be changed to `True` if this source doesn't support updating playlists (e.g., [Amazon Music module]({{< relref "user-guide/modules/amazon" >}})).

## Signals

### `status(str)`

The `status` signal can be emitted with a `str` parameter whenever some status message needs to be displayed in the application's main status bar and added to the log.

Example:

```python
self.status.emit("Please wait while the list of songs is being downloaded")
```

## Methods

### Abstract

The following methods are abstract in the interface, meaning that they must be implemented by every module.

#### `initialize(self)`

* **parameters**: none
* **returns**: None

Runs whatever is required to initialize the module.

It's used basically for loading the user's account data for each module instance after the application is restarted.

#### `getPlaylists(self)`

* **parameters**: none
* **returns**: list of dicts with the available playlists

Returns the list of playlists available in the service with the configured account.

Each playlist is represented by a dict with three keys:

* `id` — Internal id to identify the playlist under the scope of this account. Different modules and accounts can have the same `id` for some playlist, but different playlist under the same account mustn't have the same `id`.
* `name` — Display name of this playlist as it's shown to the user.
* `writable` — `True` if new items can be added to the playlist, `False` otherwise. Not used yet.

Example output:

```python
[
    {
        "id": "recent",
        "name": "Recent tracks",
        "writable": True
    },
    {
        "id": "loved",
        "name": "Loved tracks",
        "writable": True
    }
]
```

#### `getTracks(self, playlist)`

* **parameters**:
  * `playlist` — `id` of the playlist we want to get tracks from
* **returns**: list of dicts with the tracks from a playlist

If received the `id` of a playlist as returned by [`getPlaylists()`](#def-getplaylistsself) and returns the list of tracks in that playlist.

Each track is represented with the following required keys:

* `title` — Track title.
* `artist` — Performing artist.

These optional parameters are currently not used:

* `search_title` — A cleaner representation of the title more suitable for searchs (e.g., without special characters)
* `search_artist` — A cleaner representation of the artist more suitable for searchs (e.g., without special characters)
* `album` — Album where this track can be found.
* `disc` — For multi-disc albums, this is the disc number where this track can be found.
* `track` — Disc track number.
* `duration` — Track duration in seconds.
* `genre` — Track genre.

You can add any other value that may be required by your module afterwards.

Example invocation:

```python
lastfm = modules.create_object("lastfm")
lastfm = modules.setId("johndoe")
lastfm = modules.initialize()
tracks = lastfm.getTracks("loved")
```

Example output:

```python
[
    {
        'artist': 'Eminem',
        'title': 'Love The Way You Lie [feat. Rihanna] [Explicit]'
    },
    {
        'artist': 'Electric Light Orchestra',
        'title': 'Do Ya - Unedited Alternative Mix'
    },
    {
        'artist': 'Perkele',
        'title': 'I Believe'
    },
    {
        'artist': 'Discharger',
        'title': 'The Price Of Justice'
    },
    {
        'artist': 'Horace Andy',
        'title': 'I Love My Life'
    },
    {
        'artist': 'The Gaslight Anthem',
        'title': "I Coul'da Been A Contender"
    }
]
```

#### `searchTrack(self, track)`

* **parameters**:
  * `track` — dict with the details of one song
* **returns**: list of dicts with similar songs found

The `track` parameter must include the following keys:

* `search_title` or `title` — The title of the track we want to search.
* `search_artist` or `artist` — The performer of that track.

`artitst` and `title` represent the verbatim values as displayed to the user.  
`search_artist` and `search_title` provide the same values with a more search-friendly conversion as they are provided by some music services (e.g., removed special characters).

`search_artist` and `search_title` will be used if provided, failing back to their `artist` and `title` alternatives when the former ones are missing.

It returns a list of dicts with the details of each one of the songs found with a similar format as [`getTracks(playlist)`](#def-gettracksself-playlist):

* `title` — Track title.
* `artist` — Performing artist.

You can add any other value that may be required by your module afterwards.

For example, these results are used to provide the list of results that will later be used by [`addTrack( playlist, track)`](#def-addTrackself-playlist-track) to add tracks to playlists and that usually needs some identifier to be passed.

Modules that don't allow searching must still implement this method leaving it empty and reimplement `isReadOnly()` to make it return `True`:

```python
    def searchTrack(self, track):
        return False

    def isReadOnly(self):
        return True
```

Example invocation:

```python
searchTrack({'artist': 'Spice', 'title': 'So Mi Like It'})
```

Example output:

```python
[
    {
        'artist': 'Spice',
        'title': 'So Mi Like It'
    },
    {
        'artist': 'Spice',
        'title': 'So Mi Like It (Raw)'
    },
    {
        'artist': 'Spice',
        'title': 'So Mi Like It (Remix) (feat. Busta Rhymes)'
    },
    {
        'artist': 'Spice',
        'title': 'So Mi Like It (GRIMEace ReBooty)'
    },
    {
        'artist': 'Spice',
        'title': 'So Mi Like It (Extended)'
    },
    {
        'artist': 'Spice',
        'title': "So Mi Like It (Benny Page Rum'N'Riddim Remix ft. Sweetie Irie)"
    },
    {
        'artist': 'Spice',
        'title': 'So Mi Like It (Boombox Riddim)'
    },
    {
        'artist': 'Spice',
        'title': 'So Mi Like It (Clean)'
    }
]
```

#### ```addTrack(self, playlist, track)```

* **parameters**:
  * `playlist` — playlist id the song will be added to
  * `track` — whatever data is required to be provided to the module about the track that has to be added
* **returns**: `True` if the operation succeeded, `False` otherwise

Modules that don't allow adding new tracks to playlists must still implement this method leaving it empty and reimplement `isReadOnly()` to make it return `True`:

```python
    def addTrack(self, playlist, track):
        return False

    def isReadOnly(self):
        return True
```

### Public

The following methods are called by the main program and are already implemented in the interface, but can be overriden by implementations.

#### `__init(self)

* **parameters**: None
* **returns**: a `SourceModule` object

This is the object constructor.

The interface already does some initialization stuff, but a module may need to do some additional stuff.

If this method is reimplemented, it will still need to call the original constructor with `super().__init__()`.

#### `setId(self, id)`

* **parameters**:
  * `id` — Value of `__id` to use for this instance.
* **returns**: None

Sets the module `__id` property. Usually used by the main program when restoring the saved account after starting.

See also the description of the [`__id` property](#__id).

#### `getId(self)`

* **parameters**: None
* **returns**: Current `__id` of this instance.

Returns the current instance's [`__id` property](#__id).

#### `getName(self)`

* **parameters**: None
* **returns**: Current display name of this instance.

#### `getType(self)`

* **parameters**: None
* **returns**: `str` with the module name of the current instance.

Returns a string with the name of the module of this account.

#### `authenticate(self, force=False)`

* **parameters**:
  * `force` — If `True`, still carry out the authentication process regardless of the value of `isAuthenticated()`.
* **returns**: A `bool` value representing if the authentication was successful.

If `force` parameter is `True`, the module must still trigger the authentication process even if it thinks the user is still authenticated. Useful in cases when the user needs to re-authenticate, like when the authentication tokens have expired.

#### `isReadOnly(self)`

* **parameters**: None
* **returns**: A `bool` value (`False` by default) identifying if the module allows adding tracks to playlists.

Modules that don't allow making modifications to users' playlists must reimplement this method to make it return `False`:

```python
def isReadOnly(self):
    return True
```

#### `deleteAccount(self)`

* **parameters**: None
* **returns**: None

Perform any action that is required when the account is removed from muSync, like deleting stored API keys.

#### `isAuthenticated(self)`

* **parameters**: None
* **returns**: `bool` value representing if the module initialization is complete and an account to use is authenticated

#### `settings(self)`

Returns a `QSettings` object which can be used to store and recover module settings.

Example:

```python
self.settings().setValue("my_module/username", self.__username)

self.__username = self.settings().value("my_module/username")
```

See QtCore's [C++ documentation for QSettings](https://doc.qt.io/qt-5/qsettings.html) for more details.
