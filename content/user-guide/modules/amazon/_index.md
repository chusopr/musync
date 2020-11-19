+++
title = "Amazon Music"
+++
Amazon doesn't really support external applications using their service and they don't have a public API.

This module was developed by reverse-engineering their private API and that's the main reason why this project took so long.

For the same reason, there are chances this module could stop working at any moment since Amazon can decide to change their API at any moment.

That also limits the capabilities of this module. Amazon Music private API doesn't make it easy at all to search tracks to add them to a playlist, so only syncing _from_ playlists in Amazon Music is supported by this module and not syncing _to_ playlists in Amazon Music. In different words, it's a read-only module.

To add an Amazon Music account, you have to choose _Amazon Music_ as the desired source in the dialog for adding accounts:

{{< figure src="select_source.png" link="select_source.png" alt="muSync sources list" >}}

To learn how to reach this dialog and what is the workflow for adding accounts and using them in muSync, please check the [user guide]({{< relref "user-guide" >}}).

Once you do so, a browser window will be launched to authenticate to your Amazon Music account:

{{< figure src="auth.png" link="auth.png" alt="Amazon authenticate window" >}}

Once you do so, muSync will fetch your authentication cookie to be able to interact with Amazon Music API. Your credentials (username and password) are _not_ used or stored by muSync.

After your Amazon Music account is authenticated, you will have access to the songs you have added to your _My Music_ collection in Amazon Music and any other custom playlist you may have:

{{< figure src="playlist.png" link="playlist.png" alt="Amazon Music playlist" >}}

From there, the [usual process]({{< relref "user-guide" >}}) follows, with the already-mentioned distinctive feature that this module doesn't allow adding songs to playlists in Amazon Music but only reading already-existing ones to sync them to other service.
