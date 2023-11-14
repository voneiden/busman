import asyncio
import logging
from asyncio import (
    CancelledError,
    IncompleteReadError,
    Queue,
    StreamReader,
    StreamWriter,
)

from busrouter.mapper import mapper
from router import (
    NokResponse,
    OkResponse,
    PingResponse,
    PongRequest,
    PublishRequest,
    PublishResponse,
    Request,
    Response,
    SubscribeRequest,
    UnsubscribeRequest,
    route,
)

logger = logging.getLogger(__name__)


def str_to_length_prefixed_bytes(s: str) -> bytes:
    b = s.encode("ascii")
    return len(b).to_bytes(1) + b


def bytes_to_length_prefixed_bytes(b: bytes) -> bytes:
    return len(b).to_bytes(1) + b


async def handle_device_response(response_queue, writer: StreamWriter):
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


def handle_device_factory(request_queue: Queue[tuple[Queue, Request]]):
    async def handle_device(reader: StreamReader, writer: StreamWriter):
        response_queue = Queue()
        response_handler_task = asyncio.create_task(
            handle_device_response(response_queue, writer)
        )
        try:
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
                    case Request.PONG:
                        await request_queue.put((response_queue, PongRequest()))
                    case _:
                        logging.warning("Bad command, disconnect")
                        raise CloseConnection()
        except CloseConnection:
            logging.debug("Connection close requested")
        except IncompleteReadError:
            logging.warning("Incomplete read error!")
        finally:
            # TODO disconnect request
            response_handler_task.cancel()
            writer.close()
            await writer.wait_closed()
            logging.debug("Writer closed")
            try:
                await response_handler_task
            except CancelledError:
                logging.debug("Response handler cancelled")

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
    async with server:
        await server.serve_forever()


asyncio.run(main())
