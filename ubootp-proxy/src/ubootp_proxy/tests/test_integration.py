import asyncio
from asyncio import CancelledError, DatagramProtocol

import pytest

from ubootp_proxy import settings
from ubootp_proxy.ubootp_proxy import (
    main,
    create_broadcast_socket,
    mac_to_bytes,
    create_multicast_socket,
)


# TODO mock mapping response
# TODO mock broadcast address


@pytest.mark.parametrize(
    "get_socket,destination",
    [
        [
            create_broadcast_socket,
            (settings.BROADCAST_ADDRESS, settings.BROADCAST_PORT),
        ],
        [
            create_multicast_socket,
            (settings.MULTICAST_ADDRESS, settings.MULTICAST_PORT),
        ],
    ],
)
@pytest.mark.asyncio
async def test_broadcast(get_socket, destination):
    response_queue = asyncio.Queue()

    class TestProtocol(DatagramProtocol):
        received = 0

        def datagram_received(self, data, addr):
            asyncio.create_task(response_queue.put(data))
            self.received += 1

    server = asyncio.create_task(main())
    loop = asyncio.get_running_loop()
    protocol = TestProtocol()
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: protocol,
        sock=get_socket(),
    )
    test_mac = "DE:AD:DE:AD:DE:AD"
    test_mac_bytes = mac_to_bytes(test_mac)

    # Need a wee sleep here so everyone has time to join the multicast group!
    await asyncio.sleep(0.01)
    transport.sendto(b"Q" + test_mac_bytes, destination)
    async with asyncio.timeout(1):
        response = await response_queue.get()
        assert response[0] == b"Q"[0]
        response = await response_queue.get()
        assert response[0] == b"A"[0]

    assert protocol.received == 2
    server.cancel()
    try:
        await server
    except CancelledError:
        pass
