import asyncio
import logging
from asyncio import (
    CancelledError,
    IncompleteReadError,
    Queue,
    StreamReader,
    StreamWriter,
)
from typing import Optional, Coroutine

from busrouter import settings
from busrouter.mapper import mapper
from busrouter.router import (
    NokResponse,
    OkResponse,
    PingResponse,
    PongRequest,
    PublishRequest,
    PublishResponse,
    Request,
    RequestQueue,
    Response,
    ResponseQueue,
    SubscribeRequest,
    UnsubscribeRequest,
    route,
)
from busrouter.utils import set_timeout

logger = logging.getLogger(__name__)


def str_to_length_prefixed_bytes(s: str) -> bytes:
    b = s.encode("ascii")
    return len(b).to_bytes(1) + b


def bytes_to_length_prefixed_bytes(b: bytes) -> bytes:
    return len(b).to_bytes(1) + b


async def handle_device_response(response_queue: ResponseQueue, writer: StreamWriter):
    while 1:
        response = await response_queue.get()
        match response:
            case OkResponse():
                writer.write(Response.OK)
                await writer.drain()
            case NokResponse():
                writer.write(Response.NOK)
                await writer.drain()
            case PublishResponse(topic, message):
                buffer = (
                    Response.PUBLISH
                    + str_to_length_prefixed_bytes(topic)
                    + bytes_to_length_prefixed_bytes(message)
                )
                writer.write(buffer)
                await writer.drain()
            case PingResponse():
                writer.write(Response.PING)
                await writer.drain()


async def read_length_prefixed_value(reader):
    length = (await reader.readexactly(1))[0]
    if length == 0:
        return b""
    return await reader.readexactly(length)


class CloseConnection(Exception):
    pass


async def ping_task(response_queue: ResponseQueue):
    await asyncio.sleep(settings.PING_INTERVAL)
    await response_queue.put(PingResponse())


async def handle_device_request(
    request_queue: RequestQueue,
    response_queue: ResponseQueue,
    reader,
    tg: asyncio.TaskGroup,
):
    _ping_task: Optional[asyncio.Task] = None
    async with asyncio.timeout(settings.TIMEOUT) as timeout:
        while 1:
            cmd = await reader.readexactly(1)
            logging.debug(f"Recv cmd: {cmd}")
            match cmd:
                case Request.SUBSCRIBE:
                    topic = await read_length_prefixed_value(reader)
                    await request_queue.put(
                        (response_queue, SubscribeRequest(topic.decode("ascii")))
                    )
                case Request.UNSUBSCRIBE:
                    topic = await read_length_prefixed_value(reader)
                    await request_queue.put(
                        (response_queue, UnsubscribeRequest(topic.decode("ascii")))
                    )
                case Request.PUBLISH:
                    topic = await read_length_prefixed_value(reader)
                    message = await read_length_prefixed_value(reader)
                    await request_queue.put(
                        (
                            response_queue,
                            PublishRequest(topic.decode("ascii"), message),
                        )
                    )
                case b"!":
                    set_timeout(timeout, settings.TIMEOUT)
                    if _ping_task is not None and not _ping_task.done():
                        _ping_task.cancel()
                    _ping_task = tg.create_task(ping_task(response_queue))
                    await request_queue.put((response_queue, PongRequest()))

                case _:
                    logging.warning("Bad command, disconnect")
                    raise CloseConnection()


def handle_device_factory(request_queue: RequestQueue):
    async def handle_device(reader: StreamReader, writer: StreamWriter):
        response_queue: ResponseQueue = Queue()
        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(handle_device_response(response_queue, writer))
                tg.create_task(
                    handle_device_request(request_queue, response_queue, reader, tg)
                )
        except* CloseConnection:
            pass
        except* IncompleteReadError:
            logging.warning("Incomplete read error!")
        finally:
            logger.info("Closing connection")
            writer.close()
            await writer.wait_closed()

    return handle_device


async def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s]: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("app.log"),
        ],
    )

    request_queue = Queue()

    logging.info("Starting router...")
    route_task = asyncio.create_task(route(request_queue))
    # TODO handle cancel

    mapper_task = asyncio.create_task(mapper(request_queue))
    # TODO handle cancel

    HOST = "0.0.0.0"
    PORT = 42069
    server = await asyncio.start_server(
        handle_device_factory(request_queue), HOST, PORT
    )
    logging.info(f"Serving @ {HOST}:{PORT}")
    async with asyncio.TaskGroup() as tg:
        tg.create_task(route(request_queue))
        tg.create_task(mapper(request_queue))
        tg.create_task(server.serve_forever())
    # async with server:
    #    await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Good bye")
