+++
title = "Last.fm"
+++
Last.fm is currently under development and doesn't still support all the planned features.

It supports reading and updating your Last.fm Loved Tracks and reading your Recent Tracks.  
It doesn't suppor yet reading other playlists or updating your Recent Tracks.

When you try to add a Last.fm account To learn (read the [user guide]({{< relref "user-guide" >}}) for details on how to adding accounts and using them in muSync), you will be asked for your Last.fm username and password:

{{< figure src="auth.png" link="auth.png" alt="Last.fm authentication screen" >}}

Those details will _not_ be used or stored by Last.fm. Instead, the browser will take you to the screen to request an API key, which will be used by muSync to interact with Last.fm API.

This is a read-only API key that doesn't allow making changes to your Last.fm account.

Once this step is completed, you will have your Last.fm Loved and Recent Tracks in muSync:

{{< figure src="playlists.png" link="playlists.png" alt="Last.fm playlists" >}}

As mentioned before, muSync only granted read-only access to your account so far. If at some will need making changes to your Last.fm account (i.e., adding songs to a playlist), you will see a new browser window where Last.fm asks you to authenticate Last.fm to make changes to your account:

{{< figure src="authorize_application.png" link="authorize_application.png" alt="Authorize changes to your Last.fm playlists" >}}

These authorizations only last for one hour, so after that time, muSync will require a new application authorization to make changes to your playlists.
