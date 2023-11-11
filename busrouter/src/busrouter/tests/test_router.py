import asyncio
from asyncio import Queue, CancelledError
from collections import defaultdict

import pytest

from busrouter.router import (
    match_topic,
    add_route,
    remove_route,
    remove_routes,
    route,
    SubscribeRequest,
    OkResponse,
    UnsubscribeRequest,
    NokResponse,
    UnsubscribeAllRequest,
)


def test_match_topic():
    topic1 = "hello"
    topic2 = "hello/world"
    assert match_topic(topic1, topic1)
    assert match_topic(topic2, topic2)
    assert not match_topic(topic1, topic2)
    assert not match_topic(topic2, topic1)


def test_match_topic_single_wildcard():
    sub_topic = "hello/+/world"
    ok_pub_topic = "hello/foo/world"
    nok_pub_topic = "hello/world"
    nok_pub_topic2 = "hello/bar/world/thing"

    assert match_topic(sub_topic, ok_pub_topic)
    assert not match_topic(sub_topic, nok_pub_topic)
    assert not match_topic(sub_topic, nok_pub_topic2)


def test_match_topic_full_wildcard():
    sub_topic1 = "#"
    sub_topic2 = "hello/#"
    pub_topic1 = "hello/world"
    pub_topic2 = "world/hello"

    assert match_topic(sub_topic1, pub_topic1)
    assert match_topic(sub_topic1, pub_topic2)
    assert match_topic(sub_topic2, pub_topic1)
    assert not match_topic(sub_topic2, pub_topic2)


def test_add_route():
    topic_to_queues = defaultdict(list)
    queue_to_topics = defaultdict(list)
    queue = object()
    topic = "hello/world"
    add_route(topic_to_queues, queue_to_topics, queue, topic)
    assert topic in topic_to_queues
    assert topic_to_queues[topic] == [queue]
    assert queue in queue_to_topics
    assert queue_to_topics[queue] == [topic]


def test_remove_route():
    topic_to_queues = defaultdict(list)
    queue_to_topics = defaultdict(list)
    queue = object()
    queue2 = object()
    topic = "hello/world"
    topic2 = "other/world"
    add_route(topic_to_queues, queue_to_topics, queue, topic)
    add_route(topic_to_queues, queue_to_topics, queue, topic2)
    add_route(topic_to_queues, queue_to_topics, queue2, topic)
    add_route(topic_to_queues, queue_to_topics, queue2, topic2)

    assert len(queue_to_topics[queue]) == 2
    remove_route(topic_to_queues, queue_to_topics, queue, topic)
    assert len(queue_to_topics[queue]) == 1

    assert queue not in topic_to_queues[topic]
    assert queue in topic_to_queues[topic2]
    assert queue2 in topic_to_queues[topic]
    assert queue2 in topic_to_queues[topic2]

    assert len(queue_to_topics[queue2]) == 2
    remove_routes(topic_to_queues, queue_to_topics, queue2)
    assert len(queue_to_topics[queue]) == 1
    assert len(queue_to_topics[queue2]) == 0


@pytest.mark.asyncio
async def test_subscribe_and_unsubscribe_request():
    request_queue = Queue()
    response_queue = Queue()
    topic = "cool/topic"
    router = asyncio.create_task(route(request_queue))
    await request_queue.put((response_queue, SubscribeRequest(topic)))
    response = await response_queue.get()
    assert isinstance(response, OkResponse)

    await request_queue.put((response_queue, UnsubscribeRequest(topic)))
    response = await response_queue.get()
    assert isinstance(response, OkResponse)

    router.cancel()
    try:
        await router
    except CancelledError:
        pass


@pytest.mark.asyncio
async def test_unsubscribe_request_error():
    request_queue = Queue()
    response_queue = Queue()
    topic = "cool/topic"
    router = asyncio.create_task(route(request_queue))

    await request_queue.put((response_queue, UnsubscribeRequest(topic)))
    response = await response_queue.get()
    assert isinstance(response, NokResponse)

    router.cancel()
    try:
        await router
    except CancelledError:
        pass


@pytest.mark.asyncio
async def test_unsubscribe_all_request():
    request_queue = Queue()
    response_queue = Queue()
    router = asyncio.create_task(route(request_queue))

    await request_queue.put((response_queue, UnsubscribeAllRequest()))
    response = await response_queue.get()
    assert isinstance(response, OkResponse)

    router.cancel()
    try:
        await router
    except CancelledError:
        pass
