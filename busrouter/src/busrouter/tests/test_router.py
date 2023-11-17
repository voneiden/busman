import asyncio
from asyncio import CancelledError, Queue

import pytest

from busrouter.router import (
    NokResponse,
    OkResponse,
    PublishRequest,
    PublishResponse,
    RouteSegment,
    SubscribeRequest,
    UnsubscribeAllRequest,
    UnsubscribeRequest,
    add_route,
    match_route,
    remove_route,
    remove_routes,
    route,
)


def test_match_route():
    route_map = RouteSegment()
    queue = object()
    add_route(route_map, "hello/world", queue)

    assert match_route(route_map, "hello/world") == [queue]
    assert match_route(route_map, "hello/worl") == []
    assert match_route(route_map, "hello/+") == [queue]
    assert match_route(route_map, "#") == [queue]


def test_add_route():
    route_map = RouteSegment()
    queue = object()
    topic = "hello/world"
    add_route(route_map, topic, queue)

    assert "hello" in route_map
    assert "world" in route_map["hello"]
    assert route_map["hello"]["world"].routes == [queue]


def test_remove_route():
    route_map = RouteSegment()
    queue = object()
    queue2 = object()
    topic = "hello/world"
    topic2 = "other/world"
    add_route(route_map, topic, queue)
    add_route(route_map, topic2, queue)
    add_route(route_map, topic, queue2)
    add_route(route_map, topic2, queue2)

    assert route_map["hello"]["world"].routes == [queue, queue2]
    assert route_map["other"]["world"].routes == [queue, queue2]

    remove_route(route_map, topic, queue)
    assert route_map["hello"]["world"].routes == [queue2]
    assert route_map["other"]["world"].routes == [queue, queue2]

    remove_routes(route_map, queue2)
    assert route_map["hello"]["world"].routes == []
    assert route_map["other"]["world"].routes == [queue]


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


@pytest.mark.asyncio
async def test_publish():
    request_queue = Queue()
    pub_response_queue = Queue()
    sub_response_queue = Queue()
    router = asyncio.create_task(route(request_queue))
    sub_topic = "pubtest/+/topic"
    pub_topic = "pubtest/something/topic"

    message = b"testmsg"

    await request_queue.put((sub_response_queue, SubscribeRequest(sub_topic)))
    assert isinstance(await sub_response_queue.get(), OkResponse)
    await request_queue.put((pub_response_queue, PublishRequest(pub_topic, message)))
    assert isinstance(await pub_response_queue.get(), OkResponse)

    response = await sub_response_queue.get()
    assert isinstance(response, PublishResponse)
    assert response.topic == pub_topic
    assert response.message == message

    router.cancel()
    try:
        await router
    except CancelledError:
        pass
