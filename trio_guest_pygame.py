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
import sys
import traceback

import trio
import pygame
from outcome import Error

from example_tasks import get


class PygameHost:
    def __init__(self, app):
        self.app = app

    def run_sync_soon_threadsafe(self, func):
        """Use Pygame/SDL fastevent.post to schedule a function call

        The fastevent library runs a (busy?) loop trying to re-post the events if the
        queue is full, so it can result in deadlocks if called from the main thread.
        In other words, unthreaded unsafe? so we must implement run_sync_soon_not_threadsafe.
        """
        # internal convention: put it in the event __dict__ under the name "thunk"
        event = pygame.event.Event(pygame.USEREVENT, thunk=func)
        pygame.fastevent.post(event)

    def run_sync_soon_not_threadsafe(self, func):
        """Use Pygame/SDL event.post to schedule a function call

        The event queue is of finite size so for now we crash hard when that fills.
        It would be possible to make an unbounded queue for this edge case, or print
        warnings and continue while losing events, but it seems more prudent to
        just try to keep the event queue empty.

        Open question: can we use event.post with fastevent? the code seems that way.

        raises pygame.error
        """
        # internal convention: put it in the event __dict__ under the name "thunk"
        event = pygame.event.Event(pygame.USEREVENT, thunk=func)
        pygame.event.post(event)

    def done_callback(self, outcome):
        """non-blocking request to end the main loop
        """
        print(f"Outcome: {outcome}")
        if isinstance(outcome, Error):
            exc = outcome.error
            traceback.print_exception(type(exc), exc, exc.__traceback__)
        self.app.soft_landing()
        self.app.hard_landing()


class PygameDisplay:
    def __init__(self, app):
        self.app = app
        self.button_rect = pygame.Rect((235, 350), (170, 80))
        self.app.screen.fill((128, 128, 128), self.button_rect)
        self.pbar_rect = pygame.Rect((20, 20), (600, 200))
        self.app.screen.fill((0, 128, 0), self.pbar_rect)
        self.maximum = 1

    def set_title(self, title):
        pygame.display.set_caption(title)

    def set_max(self, maximum):
        self.maximum = maximum

    def set_value(self, downloaded):
        progress_ticks = 600 * downloaded // self.maximum
        progress_rect = pygame.Rect((20, 20), (progress_ticks, 200))
        self.app.screen.fill((0, 255, 0), progress_rect)

    def set_cancel(self, fn):
        self.app.register_mouse_cb(fn, self.button_rect)
        self.app.register_quit_cb(fn)


# I know it's rare to put a pygame app into a class but I wanted to match the program structure of the others
class PygameApp:
    def __init__(self):
        pygame.display.init()
        pygame.fastevent.init()
        self.screen = pygame.display.set_mode((640, 480))
        self.screen.fill((30, 30, 30))
        self.running = False
        self._mouse_cbs = []
        self._quit_cbs = []

    def mainloop(self):
        self.running = True
        while self.running:
            for event in pygame.fastevent.get():
                #print(event)
                if event.type == pygame.QUIT:
                    self.soft_landing()
                elif event.type == pygame.MOUSEBUTTONUP:
                    self._mouse_callback(event.pos, event.button)
                elif event.type == pygame.USEREVENT:
                    event.thunk()  # don't forget to add some ifs here if other USEREVENTS appear
                else:
                    pass
                    #print('unused event:', event)
            pygame.display.flip()
        pygame.quit()

    def _mouse_callback(self, pos, button):
        for cb in self._mouse_cbs:
            cb(pos, button)

    def register_mouse_cb(self, fn, rect=None, button=1):
        if rect is None:
            rect = self.screen.get_rect()

        def mousewrapper(pos, _button):
            if rect.collidepoint(pos) and button == _button:
                fn()

        self._mouse_cbs.append(mousewrapper)

    def register_quit_cb(self, fn):
        self._quit_cbs.append(fn)

    def soft_landing(self):
        for cb in self._quit_cbs:
            cb()

    def hard_landing(self):
        self.running=False


def main(url):
    app = PygameApp()
    host = PygameHost(app)
    display = PygameDisplay(app)
    trio.lowlevel.start_guest_run(
        get,
        url,
        display,
        1024 * 1024 * 1.2,
        run_sync_soon_threadsafe=host.run_sync_soon_threadsafe,
        run_sync_soon_not_threadsafe=host.run_sync_soon_not_threadsafe,
        done_callback=host.done_callback,
    )
    app.mainloop()


if __name__ == '__main__':
    main(sys.argv[1])
