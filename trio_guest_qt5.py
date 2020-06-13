# From https://gist.github.com/njsmith/d996e80b700a339e0623f97f48bcf0cb
#
# Modifications Copyright 2020 Richard J. Sheridan
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import sys
import traceback

import trio
# Can't use PySide2 currently because of
# https://bugreports.qt.io/projects/PYSIDE/issues/PYSIDE-1313
from PyQt5 import QtCore, QtWidgets
from outcome import Error

from example_tasks import get

# class Reenter(QtCore.QObject):
#     run = QtCore.Signal(object)
#
# This is substantially faster than using a signal... for some reason Qt
# signal dispatch is really slow (and relies on events underneath anyway, so
# this is strictly less work)
REENTER_EVENT = QtCore.QEvent.Type(QtCore.QEvent.registerEventType())


class ReenterEvent(QtCore.QEvent):
    pass


class Reenter(QtCore.QObject):
    def event(self, event):
        event.fn()
        return False


class QtHost:
    def __init__(self, app):
        self.app = app
        self.reenter = Reenter()
        # or if using Signal
        # self.reenter.run.connect(lambda fn: fn(), QtCore.Qt.QueuedConnection)
        # self.run_sync_soon_threadsafe = self.reenter.run.emit

    def run_sync_soon_threadsafe(self, fn):
        event = ReenterEvent(REENTER_EVENT)
        event.fn = fn
        self.app.postEvent(self.reenter, event)

    def done_callback(self, outcome):
        print(f"Outcome: {outcome}")
        if isinstance(outcome, Error):
            exc = outcome.error
            traceback.print_exception(type(exc), exc, exc.__traceback__)
        self.app.quit()


class QtDisplay:
    def __init__(self, app):
        self.app = app
        self.widget = QtWidgets.QProgressDialog(f"Fetching...", "Cancel", 0, 0)
        # Always show the dialog
        self.widget.setMinimumDuration(0)

    def set_title(self, title):
        self.widget.setLabelText(title)

    def set_max(self, maximum):
        self.widget.setMaximum(maximum)

    def set_value(self, downloaded):
        self.widget.setValue(downloaded)

    def set_cancel(self, fn):
        self.widget.canceled.connect(fn)
        # lastWindowClosed doesn't seem to matter if canceled is connected
        # Probably an artifact of the specific way QProgressDialog works
        self.app.lastWindowClosed.connect(fn)


def main(task):
    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # prevent app sudden death
    host = QtHost(app)
    display = QtDisplay(app)
    trio.lowlevel.start_guest_run(
        task,
        display,
        run_sync_soon_threadsafe=host.run_sync_soon_threadsafe,
        done_callback=host.done_callback,
    )
    app.exec_()


if __name__ == '__main__':
    main(get)
