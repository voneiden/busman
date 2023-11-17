import asyncio
import logging
from asyncio import Queue
from collections import defaultdict
from functools import lru_cache

logger = logging.getLogger(__name__)


class ParseError(Exception):
    pass


class Request:
    SUBSCRIBE = b"+"
    UNSUBSCRIBE = b"-"
    PUBLISH = b"@"
    PONG = b"!"


class SubscribeRequest(Request):
    __slots__ = ("topic",)
    __match_args__ = ("topic",)

    def __init__(self, topic: str):
        self.topic = topic


class UnsubscribeRequest(Request):
    __slots__ = ("topic",)
    __match_args__ = ("topic",)

    def __init__(self, topic: str):
        self.topic = topic


class UnsubscribeAllRequest(Request):
    __slots__ = ("skip_response",)
    __match_args__ = ("skip_response",)

    def __init__(self, skip_response=False):
        self.skip_response = skip_response


class PublishRequest(Request):
    __slots__ = ("topic", "message")
    __match_args__ = ("topic", "message")

    def __init__(self, topic: str, message: bytes):
        self.topic = topic
        self.message = message


class PongRequest(Request):
    pass


class Response:
    OK = b"k"
    NOK = b"E"
    PUBLISH = b"@"
    PING = b"?"


class OkResponse(Response):
    pass


class NokResponse(Response):
    pass


class PublishResponse(Response):
    __slots__ = ("topic", "message")
    __match_args__ = ("topic", "message")

    def __init__(self, topic: str, message: bytes):
        self.topic = topic
        self.message = message


class PingResponse(Response):
    pass


ResponseQueue = Queue[Response]
RequestQueue = Queue[tuple[ResponseQueue, Request]]


def length_prefixed_to_bytes(b: bytes) -> tuple[bytes, bytes]:
    length = int.from_bytes(b[0:1], "big")
    data = b[1 : 1 + length]
    rest = b[1 + length :]
    if len(data) != length:
        raise ParseError("Invalid length")
    return data, rest


def length_prefixed_to_str(b: bytes) -> tuple[str, bytes]:
    data, rest = length_prefixed_to_bytes(b)
    return data.decode("ascii"), rest


class RouteSegment(defaultdict):
    def __init__(self, **kwargs):
        super().__init__(lambda: RouteSegment(**kwargs), **kwargs)
        self.routes = []

    def add_route(self, key: str, queue: Queue):
        self[key].routes.append(queue)

    def remove_route(self, key: str, queue: Queue):
        try:
            self[key].routes.remove(queue)
        except ValueError:
            raise RouteChangeError("Queue was not in route")
        finally:
            if self[key].is_empty:
                del self[key]

    def change_route(self, key: str, queue: Queue, add: bool):
        if add:
            return self.add_route(key, queue)
        else:
            return self.remove_route(key, queue)

    def collect(self, segment):
        routes = []
        if segment in self:
            routes += self[segment].routes
        if "+" in self:
            routes += self["+"].routes
        if "#" in self:
            routes += self["#"].routes
        return routes

    def collect_all(self, recursive=False):
        routes = []
        for key in self.keys():
            routes += self[key].routes
            if recursive:
                routes += self[key].collect_all(recursive=True)
        return routes

    def remove_routes(self, queue: Queue):
        for key in self.keys():
            if queue in self[key].routes:
                self[key].routes.remove(queue)
            self[key].remove_routes(queue)

    @property
    def is_empty(self):
        return not len(self.routes)


class RouteChangeError(Exception):
    pass


class RouteMatchError(Exception):
    pass


def _change_route(route_segment, topic: list[str], queue: Queue, add: bool):
    match topic:
        case ["#"]:
            return route_segment.change_route("#", queue, add)
        case ["+"]:
            return route_segment.change_route("+", queue, add)
        case ["+", *rest]:
            return _change_route(route_segment["+"], rest, queue, add)
        case [segment]:
            return route_segment.change_route(segment, queue, add)
        case [segment, *rest]:
            return _change_route(route_segment[segment], rest, queue, add)
        case _:
            raise RouteChangeError(f"Unable to handle topic: {topic}")


def add_route(route_map, topic: str, queue: Queue):
    return _change_route(route_map, topic.split("/"), queue, True)


def remove_route(route_map, topic: str, queue: Queue):
    return _change_route(route_map, topic.split("/"), queue, False)


def remove_routes(route_map, queue):
    return route_map.remove_routes(queue)


def _match_route(route_segment, topic: list[str]):
    match topic:
        case ["#"]:
            return route_segment.collect_all(recursive=True)
        case ["+"]:
            return route_segment.collect_all()
        case ["+", *rest]:
            routes = []
            for segment in route_segment.keys():
                routes += _match_route(route_segment[segment], rest)
            return routes
        case [segment]:
            return route_segment.collect(segment)
        case [segment, *rest]:
            routes = []
            for segment_fork in [f for f in [segment, "+", "#"] if f in route_segment]:
                routes += _match_route(route_segment[segment_fork], rest)
            return routes
        case _:
            raise RouteMatchError(f"Unable to handle topic: {topic}")


def match_route(route_map, topic: str):
    return _match_route(route_map, topic.split("/"))


async def publish(route_map, topic, message):
    routes = match_route(route_map, topic)
    if routes:
        response = PublishResponse(topic, message)
        async with asyncio.TaskGroup() as tg:
            for response_queue in routes:
                tg.create_task(response_queue.put(response))


async def route(request_queue: RequestQueue):
    route_map = RouteSegment()

    while 1:
        response_queue, request = await request_queue.get()
        match request:
            case PublishRequest(topic, message):
                await publish(route_map, topic, message)
                await response_queue.put(OkResponse())

            case SubscribeRequest(topic):
                add_route(route_map, topic, response_queue)
                await response_queue.put(OkResponse())

            case UnsubscribeAllRequest(skip_response):
                remove_routes(route_map, response_queue)
                if not skip_response:
                    await response_queue.put(OkResponse())

            case UnsubscribeRequest(topic):
                # TODO errors
                try:
                    remove_route(route_map, topic, response_queue)
                except RouteChangeError as ex:
                    logger.info("Failed to change route", exc_info=ex)
                    await response_queue.put(NokResponse())
                else:
                    await response_queue.put(OkResponse())

        request_queue.task_done()
