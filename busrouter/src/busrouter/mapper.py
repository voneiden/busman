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
    await response_queue.get()
    # TODO Check result

    mappings = result.json()
    for mapping in mappings:
        source, sink = mapping["source"], mapping["sink"]
        await request_queue.put((response_queue, SubscribeRequest(source)))
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
