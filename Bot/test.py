import time
import asyncio


def blocking():
    asyncio.wait(5)
    print("hell yeah")


async def main():
    loop = asyncio.get_event_loop()
    fut = loop.run_in_executor(None, blocking)
    try:
        await asyncio.wait_for(fut, 2)
    except asyncio.TimeoutError:
        print("aw man")


asyncio.run(main())

# > python buggy_timeout.py
# aw man
# hell yeah