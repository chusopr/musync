# 0.9.0

* Last.fm:
  * The API now returns loved songs in a different format.
  * Some errors while requesting the session key made it impossible to add songs to playlists.
  * Reserved characters like + and & in song titles were not handled correctly.
  * Make the Recent Songs playlist read-only to avoid trying to sync songs to this playlist, which would fail.
* Amazon Music: removed. The private API was changed and the module is not working anymore.
  A public API is being developed, so not worth the effort of reverse-engineer it again.
* YouTube Music: new source module.
* Multiple bug fixes, improvements and cleanup:
  * Removed dead code and unused imports.
  * Implement many failure paths that were left just pending leading to undefined behaviour.
  * Fix race conditions and improve thread handling.
  * Comparison logic errors.
  * Improve performance and reliability for comparing songs with non-ASCII characters.
  * Move resource-intensive code out of the GUI thread to avoid the GUI getting frozen.
  * Move GUI-handling code to the GUI thread to avoid undefined behaviour.
  * Bug in songs sync progress causing it to go above 100 %.
  * Possible session cookies leak in the browser.
  * Some log messages were duplicated.
  * Selecting a new playlist while the old one was still lading caused both playlists to be mixed.
  * More stability and reliability fixes.
  * Changing the selected account was not correctly implemented.
  * Fix stale accounts for modules that no longer exist.
  * Don't allow to continue if both playlists are the same.
  * Don't try to sync songs to a read-only playlist.

# 0.8.0

* Fix dialogs' sizes and positioning.
* Replaced Selenium WebDriver with QTWebEngine removing dependency on an external Google Chrome.
* Amazon: fix authentication loop making it impossible to add new accounts.
* Update binary licenses and exclude Linux-specific modules from Windows and MacOS builds.
* Added an icon.

# 0.7.0

* Modernize code:
  * Migrate to PySide6 (Qt 6).
  * Update to Selenium 4.
  * Support Python >= 3.9.
* Fix modules:
  * Last.fm:
    * Fix username retrieval.
    * Handle CAPTCHA in API create form.
  * Amazon:
    * Fix retrieving metadata for some tracks that use a different format.
    * My Music is now for premium users only.

# 0.6.0

* Add license files for source code and binary releases.
* Switch from PyQt5 to PySide2 to avoid licensing issues.
* Search for chromedriver in a more platform-independent path.
* Fix correctly searching for modules directory indenpendently of where the main script is called from.
* Check chromedriver availability and show a warning if it's missing instead of silently failing.
* Make ICU optional because it's not supported in Windows.
* Force QWizard Classic style because Aero looks so bad in Windows.
* Use QSettings abstraction to store application settings instead of plaintext files.
* Use keyring abstraction to store credentials securely instead of plaintext files.
* Remove external dependencies loaded dynamically in Windows and MacOS binary builds.
* Add support for Python 3.9.
* Add support for Windows and MacOS binary releases.
* Improve code styling and best practices (PEP8, marking Qt slots and not accessing UI elements from threads).
* Don't use XDG icons for sync results because they are usually not available in Windows and MacOS.
* Fix allowing to progress to step 2 when step 1 is still not completed.
* Add binary releases and installer for Windows and MacOS.

# 0.5.0

First public release.

Basically, just syncs Amazon Music tracklists to Last.fm Loved Tracks.
