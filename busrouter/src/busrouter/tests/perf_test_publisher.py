import asyncio
import random
import time

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


counter = 0


async def busrouter_publisher():
    global counter
    reader, writer = await asyncio.open_connection("127.0.0.1", 42069)
    topic = get_topic()
    print("TOPIC IS", topic)
    while 1:
        writer.write(
            b"@"
            + str_to_length_prefixed_bytes(topic)
            + str_to_length_prefixed_bytes("hello")
        )
        t = time.time()
        await writer.drain()
        response = await reader.read(256)
        t2 = time.time()
        print("Response:", response)
        print("Got response in", t2 - t)
        counter += 1


multiplier = 1


async def runner():
    await asyncio.gather(*[busrouter_publisher() for _ in range(multiplier)])


start = time.time()
try:
    asyncio.run(runner())

except (RuntimeError, KeyboardInterrupt):
    pass

end = time.time()
total = counter
print("Sent", total, "requests in ", end - start, "seconds")
print(total / (end - start), "req/s")
# print(get_topic())
