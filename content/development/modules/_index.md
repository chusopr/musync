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

## Attributes

### `__id`

The module's `__id` attribute must be set to a unique identifier for each module instance.

Module instances for different accounts must have different `__id`.

For example, a Last.fm module instance for user `johndoe` will have `__id = 'lastfm-johndoe` and another instance of the same module for user `janesmith` will have `__id = 'lastfm-janesmith`.

This is also used for recoverying the account's settings when restarting the application and also by some modules to know how to initialize their instances of different accounts.

### `__authenticated`

Initially set to `False`, it must be changed to `True` only after a user is successfully signed in.

If the user authentication is no longer valid, its value must be changed back to `False` until it's again authenticated.

## Signals

### `status(str)`

The `status` signal can be emitted with a `str` parameter whenever some status message needs to be displayed in the application's main status bar and added to the log.

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

### Private

These methods are required for the module's own internal use, but may also be reimplemented if required:

#### `__set_session_file(self)`

Sets the file path where the module will store its session data, like API keys or authentication cookies.

You usually won't need to reimplement this.
