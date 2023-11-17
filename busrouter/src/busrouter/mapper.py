import asyncio
import logging
from asyncio import Queue

import httpx

from busrouter import settings

logger = logging.getLogger(__name__)

from busrouter.router import (
    Request,
    RequestQueue,
    Response,
    ResponseQueue,
    SubscribeRequest,
    UnsubscribeAllRequest,
)


class SetupError(Exception):
    pass


async def setup(request_queue: Queue, response_queue: Queue):
    async with httpx.AsyncClient() as client:
        result = await client.get(settings.MAPPER_SETUP_URL)

    if result.status_code != 200:
        raise SetupError(f"Request failed, status: {result.status_code}")

    await request_queue.put((response_queue, UnsubscribeAllRequest()))
    result = await response_queue.get()
    # Check result

    mapping = result.json()["data"]
    for source_topic, sink_topic in mapping.items():
        await request_queue.put((response_queue, SubscribeRequest(source_topic)))
        response = await response_queue.get()
        # TODO check response


async def mapper(request_queue: RequestQueue):
    response_queue: ResponseQueue = Queue()
    while 1:
        try:
            mapping = await setup(request_queue, response_queue)
            break
        except ValueError:
            logger.warning("Failed to get mapping... will retry.")
            await asyncio.sleep(1)
