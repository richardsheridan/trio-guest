# Based on https://trio.readthedocs.io/en/latest/reference-lowlevel.html#using-guest-mode-to-run-trio-on-top-of-other-event-loops
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
import traceback

import trio
import asyncio
from outcome import Error

from example_tasks import get
import tqdm


class AioHost:
    def __init__(self, loop):
        self.loop = loop
        self.done_fut = asyncio.Future()

    def run_sync_soon_threadsafe(self, func):
        self.loop.call_soon_threadsafe(func)

    def run_sync_soon_not_threadsafe(self, func):
        self.loop.call_soon(func)

    def done_callback(self, outcome):
        print(f"Outcome: {outcome}")
        if isinstance(outcome, Error):
            exc = outcome.error
            traceback.print_exception(type(exc), exc, exc.__traceback__)
        self.done_fut.set_result(outcome)


class TqdmDisplay:
    def __init__(self):
        self.pbar = tqdm.tqdm(unit='Bytes', unit_scale=1)
        self.prev_downloaded = 0

    def set_title(self, title):
        self.pbar.set_description(title)

    def set_max(self, maximum):
        self.pbar.reset(maximum)

    def set_value(self, downloaded):
        self.pbar.update(downloaded - self.prev_downloaded)
        self.prev_downloaded = downloaded

    def set_cancel(self, fn):
        """no cancel button to click for tqdm"""
        pass


async def amain(task):
    host = AioHost(asyncio.get_running_loop())
    display = TqdmDisplay()
    trio.lowlevel.start_guest_run(
        task,
        display,
        run_sync_soon_threadsafe=host.run_sync_soon_threadsafe,
        run_sync_soon_not_threadsafe=host.run_sync_soon_not_threadsafe,
        done_callback=host.done_callback,
        host_uses_signal_set_wakeup_fd=True,
    )
    outcome = await host.done_fut
    display.pbar.close()
    return outcome.unwrap()


def main(task):
    asyncio.run(amain(task))


if __name__ == '__main__':
    main(get)
