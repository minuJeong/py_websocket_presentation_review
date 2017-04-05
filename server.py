
"""
websockets testdrive

author: minu jeong
"""


import asyncio
import websockets


class MessageSession(object):

    owner = None
    session_queue = None

    def __init__(self, owner):
        self.owner = owner
        self.session_queue = asyncio.Queue()

    @property
    def websocket(self):
        return self.owner.websocket

    @property
    def broadcast_queue(self) -> asyncio.Queue:
        return self.owner.broadcast_queue

    @property
    def target_queue(self) -> asyncio.Queue:
        return self.session_queue


class BaseConsumer(MessageSession):

    async def consume(self, message) -> None:
        await self.target_queue.put(message)
        print("Consumer: {}".format(message))

    async def handler(self) -> None:
        while True:
            try:
                message = await self.websocket.recv()
                await self.consume(message)
            except websockets.exceptions.ConnectionClosed:
                print("[-] client logged out.")
                break


class BaseProducer(MessageSession):

    async def send(self) -> str:
        return await self.target_queue.get()

    async def handler(self) -> None:
        while True:
            try:
                message = await self.send()
                await self.websocket.send(message)
            except websockets.exceptions.ConnectionClosed:
                print("[-] client logged out.")
                break


class ClientConsumer(BaseConsumer):

    @property
    def target_queue(self) -> asyncio.Queue:
        return self.broadcast_queue


class ClientProducer(BaseProducer):

    @property
    def target_queue(self) -> asyncio.Queue:
        return self.session_queue


class BroadcastProducer(BaseProducer):

    @property
    def target_queue(self) -> asyncio.Queue:
        return self.broadcast_queue


class ClientHandler(object):

    websocket = None

    @property
    def broadcast_queue(self) -> asyncio.Queue:
        return self.server.broadcast_queue

    consumer = None
    producer = None
    broadcaster = None

    def __init__(self, server, websocket):
        self.server = server
        self.websocket = websocket

    async def connect(self) -> None:
        self.consumer = ClientConsumer(self)
        self.producer = ClientProducer(self)
        self.broadcaster = BroadcastProducer(self)

        await self.run_session()

    async def run_session(self) -> None:
        consumer_task = asyncio.ensure_future(self.consumer.handler())
        producer_task = asyncio.ensure_future(self.producer.handler())
        broadcast_task = asyncio.ensure_future(self.broadcaster.handler())

        done, pending = await asyncio.wait(
            [consumer_task, producer_task, broadcast_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()


class Server(object):

    PORT = 8765

    active_clients = None
    broadcast_queue = None

    async def connection_handler(self, websocket, path) -> None:
        client = ClientHandler(self, websocket)
        self.active_clients.add(client)

        print("new client connected, {}".format(client))
        print("current clients: {}".format(self.active_clients))

        await client.connect()
        self.active_clients.remove(client)

    def run(self) -> None:
        print("initializing a new server on port: {}".format(self.PORT))

        self.broadcast_queue = asyncio.Queue()
        self.active_clients = set()
        connection_serv = \
            websockets.server.serve(self.connection_handler, "localhost", self.PORT)

        asyncio.get_event_loop()\
            .run_until_complete(connection_serv)
        asyncio.get_event_loop()\
            .run_forever()


Server().run()
