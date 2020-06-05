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
import collections
import sys
import tkinter as tk
import traceback

import trio
from outcome import Error

from example_tasks import get


class TkHost:
    def __init__(self, master):
        self.master = master
        self._tk_func_name = master.register(self._tk_func)
        self._q = collections.deque()

    def _tk_func(self):
        self._q.popleft()()

    def run_sync_soon_threadsafe(self, func):
        """REALLY not sure about the thread safety here """
        # self.master.after(0, func) # does a fairly intensive wrapping to each func
        self._q.append(func)
        return self.master.call('after', 0, self._tk_func_name)

    def done_callback(self, outcome):
        """End the Tcl Thread and the Tk app.
        """
        print(f"Outcome: {outcome}")
        if isinstance(outcome, Error):
            exc = outcome.error
            traceback.print_exception(type(exc), exc, exc.__traceback__)
        self.master.destroy()


class TkDisplay:
    def __init__(self, master):
        self.master = master
        self.progress = ttk.Progressbar(root, length='6i')
        self.progress.pack(fill=tk.BOTH, expand=1)
        self.cancel_button = tk.Button(root, text='Cancel')
        self.cancel_button.pack()
        self.prev_downloaded = 0

    def set_title(self, title):
        self.master.wm_title(title)

    def set_max(self, maximum):
        self.progress.configure(maximum=maximum)

    def set_value(self, downloaded):
        self.progress.step(downloaded - self.prev_downloaded)
        self.prev_downloaded = downloaded

    def set_cancel(self, fn):
        self.cancel_button.configure(command=fn)
        self.master.protocol("WM_DELETE_WINDOW", fn) # calls .destroy() by default


if __name__ == '__main__':
    import tkinter.ttk as ttk

    root = tk.Tk()
    host = TkHost(root)
    display = TkDisplay(root)
    trio.lowlevel.start_guest_run(
        get,
        sys.argv[1],
        display,
        1024 * 1024,
        run_sync_soon_threadsafe=host.run_sync_soon_threadsafe,
        done_callback=host.done_callback,
    )

    root.mainloop()
