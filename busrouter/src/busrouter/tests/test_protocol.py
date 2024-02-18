import asyncio
from datetime import datetime, timezone, timedelta

import pytest
from freezegun import freeze_time

from busrouter import settings
from busrouter.busrouter import handle_device_request


@pytest.mark.asyncio
async def test_ping_timeout():
    reader = asyncio.StreamReader()
    request_queue = asyncio.Queue()
    response_queue = asyncio.Queue()
    now = datetime.now(timezone.utc)
    with freeze_time(now) as frozen_datetime:
        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(
                    handle_device_request(request_queue, response_queue, reader, tg)
                )
                frozen_datetime.tick(delta=timedelta(seconds=settings.TIMEOUT + 1))
                await asyncio.sleep(0)
        except* asyncio.TimeoutError:
            pass
        else:
            pytest.fail("Expected to see a TimeoutError")


@pytest.mark.asyncio
async def test_pong():
    reader = asyncio.StreamReader()
    request_queue = asyncio.Queue()
    response_queue = asyncio.Queue()
    now = datetime.now(timezone.utc)
    with freeze_time(now, tick=True) as frozen_datetime:
        await asyncio.sleep(0)
        async with asyncio.TaskGroup() as tg:
            task = tg.create_task(
                handle_device_request(request_queue, response_queue, reader, tg)
            )
            frozen_datetime.move_to(
                frozen_datetime + timedelta(seconds=settings.TIMEOUT - 5)
            )
            reader.feed_data(b"!")
            await asyncio.sleep(0)

            frozen_datetime.tick(delta=timedelta(seconds=2))
            # await asyncio.sleep(0)
            task.cancel()
