#
# Copyright 2018 Roger D. Serwy
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
import trio
import sys
import time
import httpx
from outcome import Error
import traceback

import threading
import tkinter as tk
import queue

FPS = 60


class TkHost:
    def __init__(self, root):
        """TkThread object for the root 'tkinter.Tk' object"""

        self._main_thread = threading.current_thread()
        self.root = root
        self.root.eval('package require Thread')
        self._main_thread_id = self.root.eval('thread::id')

        self._call_from_data = []  # for main thread
        self._call_from_name = self.root.register(self._call_from)
        self._thread_queue = queue.SimpleQueue()

        self._th = threading.Thread(target=self._tcl_thread)
        self._th.start()

    def _call_from(self):
        # This executes in the main thread, called from the Tcl interpreter
        self._call_from_data.pop(0)()

    def _tcl_thread(self):
        # Operates in its own thread, with its own Tcl interpreter
        # Need to download thread package from
        # https://github.com/serwy/tkthread/issues/2

        tcl = tk.Tcl()
        tcl.eval('package require Thread')

        command = f'thread::send -async {self._main_thread_id} "{self._call_from_name}"'

        while True:
            item = self._thread_queue.get()
            if item is None:
                break
            self._call_from_data.append(item)
            tcl.eval(command)

    def run_sync_soon_threadsafe(self, func):
        """Non-blocking, no-synchronization """
        self._thread_queue.put_nowait(func)

    def done_callback(self, outcome):
        """End the Tcl Thread and the Tk app.
        """
        print(f"Outcome: {outcome}")
        if isinstance(outcome, Error):
            exc = outcome.error
            traceback.print_exception(type(exc), exc, exc.__traceback__)
        self._thread_queue.put_nowait(None)  # unblock _tcl_thread queue
        self._th.join()
        self.root.destroy()


async def get(url, size_guess=1024000):
    # root is currently spooky action at a distance
    root.wm_title(f"Fetching {url}...")
    progress = ttk.Progressbar(root)
    progress.pack(fill=tk.BOTH, expand=1)
    cancel_button = tk.Button(root, text='Cancel')
    cancel_button.pack()
    with trio.CancelScope() as cscope:
        cancel_button.configure(command=cscope.cancel)
        start = time.monotonic()
        downloaded = 0
        last_screen_update = time.monotonic()
        async with httpx.AsyncClient() as client:
            async with client.stream("GET", url) as response:
                total = int(response.headers.get("content-length", size_guess))
                progress.configure(maximum=total)
                prev_downloaded = 0
                async for chunk in response.aiter_raw():
                    downloaded += len(chunk)
                    if time.monotonic() - last_screen_update > 1 / FPS:
                        progress.step(downloaded - prev_downloaded)
                        prev_downloaded = downloaded
                        last_screen_update = time.monotonic()
        end = time.monotonic()
        dur = end - start
        bytes_per_sec = downloaded / dur
        print(f"Downloaded {downloaded} bytes in {dur:.2f} seconds")
        print(f"{bytes_per_sec:.2f} bytes/sec")
    return 1


if __name__ == '__main__':
    import tkinter.ttk as ttk

    root = tk.Tk()
    host = TkHost(root)
    trio.lowlevel.start_guest_run(
        get,
        sys.argv[1],
        1024 * 1024,
        run_sync_soon_threadsafe=host.run_sync_soon_threadsafe,
        done_callback=host.done_callback,
    )

    root.mainloop()
