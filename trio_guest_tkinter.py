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

import threading
import tkinter as tk
import queue
import traceback

from outcome import Error


class TkGuest:
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

        tcl = tk.Tcl()
        tcl.eval('package require Thread')

        command = f'thread::send  {self._main_thread_id} "{self._call_from_name}"'

        while True:
            item = self._thread_queue.get()
            if item is None:
                break
            self._call_from_data.append(item)
            tcl.eval(command)

    def run_sync_soon_threadsafe(self, func):
        """Non-blocking, no-synchronization """
        self._thread_queue.put(func)

    def done_callback(self, outcome):
        """End the Tcl Thread and the Tk app.
        """
        print(f"Outcome: {outcome}")
        if isinstance(outcome, Error):
            exc = outcome.error
            traceback.print_exception(type(exc), exc, exc.__traceback__)
        self._thread_queue.put(None)  # unblock _tcl_thread queue
        self._th.join()
        self.root.destroy()
