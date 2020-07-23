# From https://gist.github.com/nosklo/af157fd26c3f927d4c173b8ed0c04dff
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
import traceback
from functools import wraps

import trio
from gi import require_version

require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib
from outcome import Error

from example_tasks import get


class GtkHost:
    def run_sync_soon_threadsafe(self, fn):
        # idle_add repeats infinitely unless fn returns False
        # Trio guest ticks return None which is good enough
        GLib.idle_add(fn)

    def done_callback(self, outcome):
        print(f"Outcome: {outcome}")
        if isinstance(outcome, Error):
            exc = outcome.error
            traceback.print_exception(type(exc), exc, exc.__traceback__)
        Gtk.main_quit()

    def mainloop(self):
        Gtk.main()


class GtkDisplay:
    def __init__(self):
        self.window = Gtk.Window()
        hbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.window.add(hbox)
        self.pbar = Gtk.ProgressBar()
        hbox.pack_start(self.pbar, True, True, 0)
        self.button = Gtk.Button.new_with_label("Cancel")
        hbox.pack_start(self.button, True, True, 0)
        self.window.show_all()
        self.maximum = 100

    def set_title(self, title):
        self.window.set_title(title)

    def set_max(self, maximum):
        self.maximum = maximum

    def set_value(self, downloaded):
        self.pbar.set_fraction(downloaded / self.maximum)

    def set_cancel(self, fn):
        @wraps(fn)
        def ignore_args(*a):
            return fn()

        self.button.connect("clicked", ignore_args)
        self.window.connect("destroy", ignore_args)


def main(task):
    host = GtkHost()
    display = GtkDisplay()
    trio.lowlevel.start_guest_run(
        task,
        display,
        run_sync_soon_threadsafe=host.run_sync_soon_threadsafe,
        done_callback=host.done_callback,
        host_uses_signal_set_wakeup_fd=True,
    )
    host.mainloop()


if __name__ == "__main__":
    main(get)
