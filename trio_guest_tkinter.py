#
# Copyright 2018 Roger D. Serwy
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

"""
tkthread
--------
Easy multithreading with Tkinter on CPython 2.7/3.x and PyPy 2.7/3.x.
Background
----------
Multithreading with `Tkinter` can often cause the following errors:
    RuntimeError: main thread is not in main loop
    RuntimeError: Calling Tcl from different apartment
    NotImplementedError: Call from another thread
This module allows Python multithreading to cooperate with Tkinter.
Usage
-----
The `tkthread` module provides the `TkThread` class,
which can synchronously interact with the main thread.
    from tkthread import tk, TkThread
    root = tk.Tk()        # create the root window
    tkt = TkThread(root)  # make the thread-safe callable
    import threading, time
    def run(func):
        threading.Thread(target=func).start()
    run(lambda:     root.wm_title('FAILURE'))
    run(lambda: tkt(root.wm_title,'SUCCESS'))
    root.update()
    time.sleep(2)  # _tkinter.c:WaitForMainloop fails
    root.mainloop()
There is an optional `.install()` method on `TkThread` which
intercepts Python-to-Tk calls. This must be called on the
default root, before the creation of child widgets. There is
a slight performance penalty for Tkinter widgets that operate only
on the main thread.
"""
import functools
import threading
import tkinter as tk
import queue


class TkThread(object):
    def __init__(self, root):
        """TkThread object for the root 'tkinter.Tk' object"""

        self._main_thread = threading.current_thread()
        self.root = root
        self.root.eval('package require Thread')
        self._main_thread_id = self.root.eval('thread::id')

        self._call_from_data = []  # for main thread
        self._call_from_name = self.root.register(self._call_from)
        self._thread_queue = queue.SimpleQueue()

        self._running = True
        self._th = threading.Thread(target=self._tcl_thread)
        self._th.daemon = True
        self._th.start()

    def _call_from(self):
        # This executes in the main thread, called from the Tcl interpreter
        func, args, kwargs, tres = self._call_from_data.pop(0)
        func(*args, **kwargs)

    def _tcl_thread(self):
        # Operates in its own thread, with its own Tcl interpreter

        tcl = tk.Tcl()
        tcl.eval('package require Thread')

        command = 'thread::send  %s "%s"' % (self._main_thread_id,
                                             self._call_from_name)
        while self._running:
            item = self._thread_queue.get()
            if item is None:
                break
            self._call_from_data.append(item)
            tcl.eval(command)

    def nosync(self, func, *args, **kwargs):
        """Non-blocking, no-synchronization """
        self._thread_queue.put((func, args, kwargs, None))

    def destroy(self):
        """Destroy the TkThread object.
        """
        self._running = False
        self._thread_queue.put(None)  # unblock _tcl_thread queue
