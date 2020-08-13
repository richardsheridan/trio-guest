import math
import sys
import time
import warnings
from functools import partial

import httpx
import trio
import httpcore._async.http11

# Default is 4096
httpcore._async.http11.AsyncHTTP11Connection.READ_NUM_BYTES = 100_000


async def get(display):
    try:
        url = sys.argv[1]
    except IndexError:
        url = "http://google.com/"
    try:
        size_guess = int(sys.argv[2])
    except IndexError:
        size_guess = 5269
    fps = 60
    display.set_title(f"Fetching {url}...")
    with trio.CancelScope() as cscope:
        display.set_cancel(cscope.cancel)
        start = time.monotonic()
        downloaded = 0
        last_screen_update = time.monotonic()
        async with httpx.AsyncClient() as client:
            for i in range(10):
                print("Connection attempt", i)
                try:
                    async with client.stream("GET", url) as response:
                        total = int(response.headers.get("content-length", size_guess))
                        display.set_max(total)
                        async for chunk in response.aiter_raw():
                            downloaded += len(chunk)
                            if time.monotonic() - last_screen_update > 1 / fps:
                                display.set_value(downloaded)
                                last_screen_update = time.monotonic()
                    break
                except httpcore._exceptions.ReadTimeout:
                    pass
            else:
                print("response timed out 10 times")
                return
        end = time.monotonic()
        dur = end - start
        bytes_per_sec = downloaded / dur
        print(f"Downloaded {downloaded} bytes in {dur:.2f} seconds")
        print(f"{bytes_per_sec:.2f} bytes/sec")
    return 1


async def count(display, period=.1, max=60):
    display.set_title(f"Counting every {period} seconds...")
    display.set_max(60)
    with trio.CancelScope() as cancel_scope:
        display.set_cancel(cancel_scope.cancel)
        for i in range(max):
            await trio.sleep(period)
            display.set_value(i)
    return 1


async def check_latency(display=None, period=0.1, duration=math.inf):
    with trio.move_on_after(duration) as cscope:
        if display is not None:
            display.set_cancel(cscope.cancel)
        elif duration == math.inf:
            warnings.warn("check_latency may not terminate until the process is killed")
        while True:
            target = trio.current_time() + period
            await trio.sleep_until(target)
            print(trio.current_time() - target, flush=True)


if __name__ == '__main__':
    trio.run(partial(check_latency,duration=2,))
