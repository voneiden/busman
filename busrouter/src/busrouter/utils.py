import asyncio


def set_timeout(timeout: asyncio.Timeout, seconds):
    loop = asyncio.get_running_loop()
    timeout.reschedule(seconds + loop.time())
