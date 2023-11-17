import asyncio
import random

base_topic = "testing/with/a/long/test/topic/".split("/")


def str_to_length_prefixed_bytes(s: str) -> bytes:
    b = s.encode("ascii")
    return len(b).to_bytes(1) + b


def get_topic():
    topic = []
    for segment in base_topic:
        if random.random() > 0.95:
            topic.append("#")
            break
        elif random.random() > 0.8:
            topic.append("+")
        else:
            topic.append(segment)

    return "/".join(topic)


def get_topic():
    return "hi"


async def busrouter_subscriber():
    reader, writer = await asyncio.open_connection("127.0.0.1", 42069)
    topic = get_topic()
    writer.write(b"+" + str_to_length_prefixed_bytes(topic))
    await writer.drain()

    while True:
        data = await reader.read(256)
        print(f"Received: {data.decode()!r}")


async def main():
    # Schedule three calls *concurrently*:
    tasks = [busrouter_subscriber() for _ in range(1)]
    await asyncio.gather(*tasks)


asyncio.run(main())
