from asyncio import Queue
from collections import defaultdict
from functools import cache, lru_cache
from random import random
import logging

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

    def __init__(self, topic: str, message: bytes):
        self.topic = topic
        self.message = message


class PingResponse(Response):
    pass


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


def _match_topic(sub_topic: list[str], pub_topic: list[str]):
    match (sub_topic, pub_topic):
        case [["#", *_], _]:
            return True
        case [["+", *sub_rest], [_, *pub_rest]]:
            return _match_topic(sub_rest, pub_rest)
        case [[sub, *sub_rest], [pub, *pub_rest]] if sub == pub:
            return _match_topic(sub_rest, pub_rest)
        case [[], []]:
            return True
        case _:
            return False


@lru_cache(1024)
def match_topic(sub_topic: str, pub_topic: str):
    """
    Oce the lru_cache is warm, it's about 24x faster for
    a topic with three words.
    """
    sub_topic = sub_topic.split("/")
    pub_topic = pub_topic.split("/")
    return _match_topic(sub_topic, pub_topic)


def remove_routes(topic_to_queues, queue_to_topics, queue):
    if queue not in queue_to_topics:
        return

    topics = queue_to_topics[queue]
    del queue_to_topics[queue]

    for topic in topics:
        topic_queues = topic_to_queues[topic]
        topic_queues.remove(queue)
        if len(topic_queues) == 0:
            del topic_to_queues[topic]

    return


class RemoveRouteError(Exception):
    pass


def remove_route(topic_to_queues, queue_to_topics, queue, topic):
    if queue not in queue_to_topics:
        raise RemoveRouteError("Queue is not subscribed to anything")

    queue_topics = queue_to_topics[queue]
    if topic not in queue_topics:
        raise RemoveRouteError("Queue is not subscribed to topic")

    queue_topics.remove(topic)
    if len(queue_topics) == 0:
        del queue_to_topics[queue]

    topic_queues = topic_to_queues[topic]
    topic_queues.remove(queue)
    if len(topic_queues) == 0:
        del topic_to_queues[topic]


def add_route(topic_to_queues, queue_to_topics, queue, topic):
    topic_to_queues[topic].append(queue)
    queue_to_topics[queue].append(topic)


async def publish(topic_to_queues, pub_topic, message):
    response = PublishResponse(pub_topic, message)
    for sub_topic, queues in topic_to_queues.items():
        if match_topic(sub_topic, pub_topic):
            for queue in queues:
                await queue.put(response)


async def route(request_queue: Queue[tuple[Queue, Request]]):
    topic_to_queues: dict[str, list[Queue]] = defaultdict(list)
    queue_to_topics: dict[Queue, list[str]] = defaultdict(list)

    while 1:
        response_queue, request = await request_queue.get()
        match request:
            case PublishRequest(topic, message):
                await publish(topic_to_queues, topic, message)

            case SubscribeRequest(topic):
                add_route(topic_to_queues, queue_to_topics, response_queue, topic)
                await response_queue.put(OkResponse())
            case UnsubscribeAllRequest(skip_response):
                remove_routes(topic_to_queues, queue_to_topics, response_queue)
                if not skip_response:
                    await response_queue.put(OkResponse())
            case UnsubscribeRequest(topic):
                try:
                    remove_route(
                        topic_to_queues, queue_to_topics, response_queue, topic
                    )
                except RemoveRouteError as ex:
                    logger.warning("Failed to remove route:", exc_info=ex)
                    await response_queue.put(NokResponse())
                else:
                    await response_queue.put(OkResponse())

        request_queue.task_done()


class Router:
    def __init__(self, request_queue: Queue):
        pass

    def subscribe(self, topic, transport):
        pass
