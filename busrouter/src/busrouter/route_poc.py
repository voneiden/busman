# So here's an interesting idea: to build a hash tree of the routes
import asyncio
from asyncio import Queue
from collections import defaultdict

from busrouter.router import (
    Request,
    PublishRequest,
    PublishResponse,
    OkResponse,
    SubscribeRequest,
    UnsubscribeAllRequest,
    UnsubscribeRequest,
)


class RouteSegment(defaultdict):
    def __init__(self, **kwargs):
        super().__init__(lambda: RouteSegment(**kwargs), **kwargs)
        self.routes = []

    def add_route(self, key: str, queue: Queue):
        self[key].routes.append(queue)

    def remove_route(self, key: str, queue: Queue):
        self[key].routes.remove(queue)
        if self[key].is_empty:
            del self[key]

    def change_route(self, key: str, queue: Queue, add: bool):
        if add:
            return self.add_route(key, queue)
        else:
            return self.remove_route(key, queue)

    def collect_all(self, recursive=True):
        routes = []
        for key in self.keys():
            routes += self[key].routes
            if recursive:
                routes += self[key].collect_all(recursive=True)
        return routes

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
    # TODO
    return


def _match_route(route_segment, topic: list[str]):
    match topic:
        case ["#"]:
            return route_segment.collect_all(recursive=True)
        case ["+"]:
            return route_segment.collect_all()
        case ["+", *rest]:
            routes = route_segment.collect_all()
            for segment in route_segment.keys():
                routes += _match_route(route_segment[segment], rest)
            return routes
        case [segment]:
            return route_segment[segment].routes
        case [segment, *rest]:
            return route_segment[segment].routes + _match_route(
                route_segment[segment], rest
            )
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


async def route(request_queue: Queue[tuple[Queue, Request]]):
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
                remove_route(route_map, topic, response_queue)
                # await response_queue.put(NokResponse())
                await response_queue.put(OkResponse())

        request_queue.task_done()
