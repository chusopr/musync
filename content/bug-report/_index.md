+++
title = "Reporting bugs"
weight = 3
+++
You can report bugs in [GitHub issue tracker](https://github.com/chusopr/musync/issues).

When reporting bugs, please provide as many details as possible, like:

* What exactly you were doing when the error happened.
* If the error is related to some song, please include the exact verbatim artist and title in the report.
* Include a copy of the logs:
  1. Click on the _Logs_ button in the main screen:
     {{< figure src="logs_button.png" link="logs_button.png" alt="muSync Logs button" >}}
  2. When the logs window opens, click on the _Copy_ button and paste it on a text document that you will upload to the bug report:
     {{< figure src="logs.png" link="logs.png" alt="muSync logs" >}}
* Run the application from the command line and include any output it generates, for example:
```
$ musync.py 
Traceback (most recent call last):
  File "/home/jprey/musync/modules/amazon/__init__.py", line 124, in authenticate
    element = wait.until(amzn_object_exists())
  File "/usr/lib/python3.7/site-packages/selenium/webdriver/support/wait.py", line 71, in until
    value = method(self._driver)
  File "/home/jprey/musync/modules/amazon/__init__.py", line 10, in __call__
    return driver.execute_script('return typeof amznMusic !== "undefined" && "appConfig" in amznMusic && "customerId" in amznMusic.appConfig;')
  File "/usr/lib/python3.7/site-packages/selenium/webdriver/remote/webdriver.py", line 636, in execute_script
    'args': converted_args})['value']
  File "/usr/lib/python3.7/site-packages/selenium/webdriver/remote/webdriver.py", line 321, in execute
    self.error_handler.check_response(response)
  File "/usr/lib/python3.7/site-packages/selenium/webdriver/remote/errorhandler.py", line 242, in check_response
    raise exception_class(message, screen, stacktrace)
selenium.common.exceptions.WebDriverException: Message: chrome not reachable
  (Session info: chrome=86.0.4240.111)


During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/home/jprey/musync/wizard/page1.py", line 75, in <lambda>
    accountsDialog.account_selected.connect(lambda account: self.__account_selected(side, account))
  File "/home/jprey/musync/wizard/page1.py", line 48, in __account_selected
    playlists = account.getPlaylists()
  File "/home/jprey/musync/modules/amazon/__init__.py", line 177, in getPlaylists
    playlists_request = self.__request("cloudplayer/playlists/", "com.amazon.musicplaylist.model.MusicPlaylistService.getOwnedPlaylistsInLibrary")
  File "/home/jprey/musync/modules/amazon/__init__.py", line 97, in __request
    return self.__request(endpoint, target, data, headers, True)
  File "/home/jprey/musync/modules/amazon/__init__.py", line 75, in __request
    if not self.authenticate(force=True):
  File "/home/jprey/musync/modules/amazon/__init__.py", line 128, in authenticate
    self.status.emit(e)
TypeError: SourceModule.status[str].emit(): argument 1 has unexpected type 'WebDriverException'
Aborted
```
