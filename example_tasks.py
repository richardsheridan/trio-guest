import time

import httpx
import trio
import httpcore._async.http11

# Default is 4096
httpcore._async.http11.AsyncHTTP11Connection.READ_NUM_BYTES = 100_000


async def get(url, display, size_guess=1024000):
    fps = 60
    display.set_title(f"Fetching {url}...")
    with trio.CancelScope() as cscope:
        display.set_cancel(cscope.cancel)
        start = time.monotonic()
        downloaded = 0
        last_screen_update = time.monotonic()
        async with httpx.AsyncClient() as client:
            async with client.stream("GET", url) as response:
                total = int(response.headers.get("content-length", size_guess))
                display.set_max(total)
                async for chunk in response.aiter_raw():
                    downloaded += len(chunk)
                    if time.monotonic() - last_screen_update > 1 / fps:
                        display.set_value(downloaded)
                        last_screen_update = time.monotonic()
        end = time.monotonic()
        dur = end - start
        bytes_per_sec = downloaded / dur
        print(f"Downloaded {downloaded} bytes in {dur:.2f} seconds")
        print(f"{bytes_per_sec:.2f} bytes/sec")
    return 1


async def check_latency(frequency, duration):
    with trio.move_on_after(duration):
        while True:
            target = trio.current_time() + frequency
            await trio.sleep_until(target)
            print(trio.current_time() - target, flush=True)


if __name__ == '__main__':
    trio.run(check_latency, .01, 1)
