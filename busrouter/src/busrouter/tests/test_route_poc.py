from busrouter.route_poc import RouteSegment, add_route, match_route


def test_something():
    route_map = RouteSegment()
    queue = object()
    add_route(route_map, "hello/world", queue)

    assert match_route(route_map, "hello/world") == [queue]
    assert match_route(route_map, "hello/worl") == []
    assert match_route(route_map, "hello/+") == [queue]
    assert match_route(route_map, "#") == [queue]
