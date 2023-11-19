import asyncio
import socket
import struct
from asyncio import DatagramProtocol, DatagramTransport
import httpx
from ubootp_proxy import settings

import logging

logger = logging.getLogger(__name__)


def create_multicast_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((settings.MULTICAST_BIND, settings.MULTICAST_PORT))
    # group = socket.inet_aton(settings.MULTICAST_ADDRESS)
    # mreq = group + socket.inet_aton(settings.MULTICAST_BIND)
    mreq = struct.pack(
        "4sL", socket.inet_aton(settings.MULTICAST_ADDRESS), socket.INADDR_ANY
    )
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    return sock


def create_broadcast_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(("255.255.255.255", settings.MULTICAST_PORT))
    return sock


def bytes_to_mac(bs):
    return ":".join(hex(b)[2:] for b in bs)


def mac_to_bytes(mac):
    return bytes(int(h, 16) for h in mac.split(":"))


def ip_to_bytes(ip):
    return bytes(int(h) for h in ip.split("."))


class UbootpProtocol(DatagramProtocol):
    transport: DatagramTransport
    destination: tuple[str, int]

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        # Expected length is 7
        if len(data) != 7:
            logger.warning(f"Received incorrect datagram length ({len(data)})")
            return

        if data[0] != b"Q"[0]:
            logger.debug("Received message is not a query")
            return

        asyncio.create_task(self.process_request(data[1:]))

    async def process_request(self, data):
        mac = bytes_to_mac(data)
        # Request configuration

        mock_ip = "192.168.69.123"
        mock_mask = "255.255.255.0"
        mock_gw = "192.168.69.1"

        buf = [
            b"A",
            data,
            ip_to_bytes(mock_ip),
            ip_to_bytes(mock_mask),
            ip_to_bytes(mock_gw),
        ]
        # Send response
        self.transport.sendto(b"".join(buf), self.destination)


class UbootpMulticastProtocol(UbootpProtocol):
    destination = (settings.MULTICAST_ADDRESS, settings.MULTICAST_PORT)


class UbootpBroadcastProtocol(UbootpProtocol):
    destination = (settings.BROADCAST_ADDRESS, settings.BROADCAST_PORT)


async def main():
    print("Starting up")
    loop = asyncio.get_running_loop()

    print("Firing up ubootp service")
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: UbootpBroadcastProtocol(),
        sock=create_broadcast_socket(),
    )

    multicast_transport, multicast_protocol = await loop.create_datagram_endpoint(
        lambda: UbootpMulticastProtocol(),
        sock=create_multicast_socket(),
    )

    try:
        await asyncio.Future()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt, quitting")
        transport.close()
        multicast_transport.close()


if __name__ == "__main__":
    asyncio.run(main())
