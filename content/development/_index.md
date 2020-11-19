+++
title = "Development guide"
weight = 2
+++
muSync is currently developed with [PyQt5](https://www.riverbankcomputing.com/software/pyqt), although a migration to [PySide2](https://wiki.qt.io/PySide2) is planned due to licensing concerns.

At this moment, the development focused mainly on the success path until it was possible to check the goal was achievable, so there is no very good error control. In different words, if you try to make it fail, it will probably fail horribly.

A modular model was taken for providing support for each music service. That means that the support for different music services is implement with a module for that service.

That eases the maintenance of each service separatedly and also allows third-party development of support for additional music services.

Check the [modules development guide]({{< relref "development/modules" >}}) for details on how modules work and how a new module can be developed.

Last.fm is the reference implementation due to the simplicity and ease of use of its API, although the implementation is still not complete.  
Check the [Last.fm module user guide]({{< relref "user-guide/modules/lastfm" >}}) for details on implemented features.
