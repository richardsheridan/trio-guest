# From https://gist.github.com/njsmith/d996e80b700a339e0623f97f48bcf0cb

import trio
import sys
import time
import httpx
from outcome import Error
import traceback

# Can't use PySide2 currently because of
# https://bugreports.qt.io/projects/PYSIDE/issues/PYSIDE-1313
from PyQt5 import QtCore, QtWidgets

import httpcore._async.http11

# Default is 4096
httpcore._async.http11.AsyncHTTP11Connection.READ_NUM_BYTES = 100_000

FPS = 60

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


async def get(url, size_guess=1024000):
    dialog = QtWidgets.QProgressDialog(f"Fetching {url}...", "Cancel", 0, 0)
    # Always show the dialog
    dialog.setMinimumDuration(0)
    with trio.CancelScope() as cscope:
        dialog.canceled.connect(cscope.cancel)
        start = time.monotonic()
        downloaded = 0
        last_screen_update = time.monotonic()
        async with httpx.AsyncClient() as client:
            async with client.stream("GET", url) as response:
                total = int(response.headers.get("content-length", size_guess))
                dialog.setMaximum(total)
                async for chunk in response.aiter_raw():
                    downloaded += len(chunk)
                    if time.monotonic() - last_screen_update > 1 / FPS:
                        dialog.setValue(downloaded)
                        last_screen_update = time.monotonic()
        end = time.monotonic()
        dur = end - start
        bytes_per_sec = downloaded / dur
        print(f"Downloaded {downloaded} bytes in {dur:.2f} seconds")
        print(f"{bytes_per_sec:.2f} bytes/sec")
    return 1


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    host = QtHost(app)
    trio.lowlevel.start_guest_run(
        get,
        sys.argv[1],
        1024*1024,
        run_sync_soon_threadsafe=host.run_sync_soon_threadsafe,
        done_callback=host.done_callback,
    )

    app.exec_()
