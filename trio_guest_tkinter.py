#
# Copyright 2020 Richard J. Sheridan
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
import tkinter as tk
import traceback

import trio
from outcome import Error

from example_tasks import get


class TkHost:
    def __init__(self, root):
        self.root = root
        self._tk_func_name = root.register(self._tk_func)
        self._q = collections.deque()

    def _tk_func(self):
        self._q.popleft()()

    def run_sync_soon_threadsafe(self, func):
        """Use Tcl "after" command to schedule a function call

        Based on `tkinter source comments <https://github.com/python/cpython/blob/a5d6aba318ead9cc756ba750a70da41f5def3f8f/Modules/_tkinter.c#L1472-L1555>`_
        the issuance of the tcl call to after itself is thread-safe since it is sent
        to the `appropriate thread <https://github.com/python/cpython/blob/a5d6aba318ead9cc756ba750a70da41f5def3f8f/Modules/_tkinter.c#L814-L824>`_ on line 1522.

        Compare to `tkthread <https://github.com/serwy/tkthread/blob/1f612e1dd46e770bd0d0bb64d7ecb6a0f04875a3/tkthread/__init__.py#L163>`_
        where definitely thread unsafe `eval <https://github.com/python/cpython/blob/a5d6aba318ead9cc756ba750a70da41f5def3f8f/Modules/_tkinter.c#L1567-L1585>`_
        is used to send thread safe signals between tcl interpreters.

        If .call is called from the Tcl thread, the locking and sending are optimized away
        so it should be fast enough that the run_sync_soon_not_threadsafe version is unnecessary.
        """
        # self.master.after(0, func) # does a fairly intensive wrapping to each func
        self._q.append(func)
        self.root.call('after', 0, self._tk_func_name)

    def run_sync_soon_not_threadsafe(self, func):
        """Use Tcl "after" command to schedule a function call from the main thread

        Not sure if this is actually an optimization because Tcl parses this eval string fresh each time.
        However it's definitely thread unsafe because the string is fed directly into the Tcl interpreter
        from the current Python thread
        """
        self._q.append(func)
        self.root.eval(f'after 0 {self._tk_func_name}')

    def done_callback(self, outcome):
        """End the Tk app.
        """
        print(f"Outcome: {outcome}")
        if isinstance(outcome, Error):
            exc = outcome.error
            traceback.print_exception(type(exc), exc, exc.__traceback__)
        self.root.destroy()

    def mainloop(self):
        self.root.mainloop()


class TkDisplay:
    def __init__(self, master):
        import tkinter.ttk as ttk

        self.master = master
        self.progress = ttk.Progressbar(master, length='6i')
        self.progress.pack(fill=tk.BOTH, expand=1)
        self.cancel_button = tk.Button(master, text='Cancel')
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
        self.master.protocol("WM_DELETE_WINDOW", fn)  # calls .destroy() by default


def main(task):
    root = tk.Tk()
    host = TkHost(root)
    display = TkDisplay(root)
    trio.lowlevel.start_guest_run(
        task,
        display,
        run_sync_soon_threadsafe=host.run_sync_soon_threadsafe,
        # run_sync_soon_not_threadsafe=host.run_sync_soon_not_threadsafe,  # currently recommend threadsafe only
        done_callback=host.done_callback,
    )
    host.mainloop()


if __name__ == '__main__':
    main(get)
