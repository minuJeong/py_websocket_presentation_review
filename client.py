
"""
websockets testdrive

author: minu jeong
"""

import asyncio
import websockets

from PyQt5 import QtWidgets
from PyQt5 import QtCore


class NetworkHandler(QtCore.QThread):

    PORT = 8765

    server_push_signal = QtCore.pyqtSignal(str)

    _websocket = None

    @property
    def websocket(self):
        if not self._websocket:
            self.connect()
        return self._websocket

    async def listen_server_push(self) -> None:
        while True:
            server_push_message = await self.websocket.recv()
            print(f"Server Message: {server_push_message}")
            self.server_push_signal.emit(server_push_message)

    def run(self) -> None:
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        connect_task = asyncio.ensure_future(self.connect())
        self.loop.run_until_complete(connect_task)

        listener_task = asyncio.ensure_future(self.listen_server_push())
        self.loop.run_until_complete(listener_task)

    async def connect(self) -> bool:
        print("Attempt to connect..")
        self._websocket = await websockets.client.connect(f"ws://localhost:{self.PORT}")

        # TODO: return False if failed
        print("Connected!")
        return True

    async def send_message(self, message) -> None:
        await self.websocket.send(message)

    async def close(self) -> None:
        await self.websocket.close(reason="actively logged out")


class MainWindow(QtWidgets.QWidget):

    network_handler = None

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        self.mainlayout = QtWidgets.QVBoxLayout()

        self.connect_btn = QtWidgets.QPushButton("Connect")
        self.mainlayout.addWidget(self.connect_btn)
        self.connect_btn.clicked.connect(self.try_connect)

        self.history_tree = QtWidgets.QTreeWidget()
        self.mainlayout.addWidget(self.history_tree)

        self.message_input = QtWidgets.QLineEdit()
        self.mainlayout.addWidget(self.message_input)

        self.send_btn = QtWidgets.QPushButton("Send")
        self.mainlayout.addWidget(self.send_btn)
        self.send_btn.setEnabled(False)
        self.send_btn.clicked.connect(self.try_send_message)

        self.exit_btn = QtWidgets.QPushButton("Close")
        self.mainlayout.addWidget(self.exit_btn)
        self.exit_btn.clicked.connect(self.try_close)

        self.setLayout(self.mainlayout)

        self.network_handler = NetworkHandler()
        self.network_handler.server_push_signal.connect(self.on_server_push)

    def try_connect(self, is_checked) -> None:
        self.connect_btn.setEnabled(False)
        self.network_handler.start()
        self.send_btn.setEnabled(True)

    def try_send_message(self, is_checked) -> None:
        self.send_btn.setEnabled(False)

        message = str(self.message_input.text())
        if not message:
            return

        task = asyncio.ensure_future(self.network_handler.send_message(message))
        asyncio.get_event_loop().run_until_complete(task)

        self.send_btn.setEnabled(True)

    def try_close(self, is_checked) -> None:

        task = asyncio.ensure_future(self.network_handler.close())
        asyncio.get_event_loop().run_until_complete(task)

        self.close()

    def on_server_push(self, message) -> None:
        print(f"Server message: {message}")

        history = QtWidgets.QTreeWidgetItem(0)
        history.setText(0, message)
        self.history_tree.addTopLevelItem(history)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    mainwin = MainWindow()
    mainwin.show()
    app.exec()
