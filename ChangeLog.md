# 0.6.0

* Add license file.
* Switch from PyQt5 to PySide2 to avoid licensing issues.
* Search for chromedriver in a more platform-independent path.
* Fix correctly searching for modules directory idenpendently of where the main script is called from.
* Check chromedriver availability and show a warning if it's missing instead of silently failing.
* Make ICU optional because it's not supported in Windows.
* Force QWizard Classic style because Aero looks so bad in Windows.
* Use QSettings abtraction to store application settings instead of plaintext files.
* Use keyring abstraction to store credentials securely instead of plaintext files.
* Remove external dependencies loaded dynamically in Windows and MacOS binary builds.
* Add support for Python 3.9.
* Add support for Windows and MacOS binary releases.
* Improve code styling and best practices (PEP8, marking Qt slots and not accessing UI elements from threads).
* Don't use XDG icons for sync results because they are usually not available in Windows and MacOS.
* Fix allowing to progress to step 2 when step 1 is still not completed.

# 0.5.0

First public release.

Basically, just syncs Amazon Music tracklists to Last.fm Loved Tracks.
