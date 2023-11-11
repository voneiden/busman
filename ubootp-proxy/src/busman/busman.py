import asyncio
import socket
from asyncio import DatagramProtocol, DatagramTransport

from busman import settings


def create_ubootp_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((settings.UBOOTP_BIND, settings.UBOOTP_PORT))
    group = socket.inet_aton(settings.UBOOTP_ADDRESS)
    mreq = group + socket.inet_aton(settings.UBOOTP_BIND)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)


class EchoServerProtocol(DatagramProtocol):
    transport: DatagramTransport

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        message = data.decode()
        print("Received %r from %s" % (message, addr))
        print("Send %r to %s" % (message, addr))
        self.transport.sendto(data, addr)


async def main():
    print("Starting up")
    loop = asyncio.get_running_loop()

    print("Firing up ubootp service")
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: EchoServerProtocol(),
        sock=create_ubootp_socket(),
    )

    try:
        await asyncio.sleep(3600)  # Serve for 1 hour.
    finally:
        transport.close()


asyncio.run(main())
