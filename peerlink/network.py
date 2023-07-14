import selectors
import socket
from logging import exception
from threading import Thread

from peerlink.utils import Signal

LOCAL_IP = socket.gethostbyname_ex(socket.getfqdn())[2][0]


class Reciever(Thread):
    def __init__(self, host: str = "", port: int = 8080, backlog: int = 0) -> None:
        super().__init__(name="reciever", daemon=True)
        self.addr = (host, port)
        self.selector = selectors.DefaultSelector()
        self.socket = socket.socket()
        self.clients = []
        self._bind(host, port, backlog)
        self.onconnection = Signal("sock")
        self.ondata = Signal("data","sock")

        self.socket.setblocking(False)

    def _accept(self, sock: socket.socket):
        conn, addr = sock.accept()
        print(addr," Connected")
        self.clients.append(conn)
        conn.setblocking(False)
        self.selector.register(conn, selectors.EVENT_READ, self._read)

        self.onconnection.emit(conn)

    def _read(self, sock):
        try:
            data = sock.recv(1024)
            print("Recieved ",data)
        except ConnectionResetError as e:
            exception('Connection closed by remote peer.')
            self.selector.unregister(sock)
            self.clients.remove(sock)
            return
        except socket.error as e:
            exception('')
        if data:
            self.ondata.emit(data,sock)
        else:
            self.selector.unregister(sock)
            self.clients.remove(sock)

    def _bind(self, host, port, backlog):
        try:
            self.socket.bind((host, port))
            self.socket.listen(backlog)
        except socket.error as e:
            exception("Couldn't bind socket.")

    def disconnect_except(self, sock):
        for client in self.clients:
            if sock != client:
                self.selector.unregister(client)

    def run(self):
        self.selector.register(self.socket, selectors.EVENT_READ, self._accept)
        while True:
            for key, mask in self.selector.select(1.0):
                callback = key.data
                callback(key.fileobj)


class Sender:
    def __init__(self, host, port) -> None:
        self.socket = socket.socket()
        self.onerror = Signal()
        if isinstance(host, bytes):
            host = socket.inet_ntoa(host)
        self.addr = (host, port)

    def try_block(func):
        def wrapper(self, *args):
            try:
                func(self, *args)
            except socket.error as e:
                self.onerror.emit()
                exception("")
        return wrapper

    def connect(self):
        try:
            self.socket.connect(self.addr)
            return self
        except ConnectionRefusedError as e:
            exception('Connection Refused')
            return False

    @classmethod
    def send_query(cls, host: str, port: int, payload: bytes):
        tmp = cls(host, port)
        try:
            if tmp.connect():
                tmp.socket.sendall(payload)
                return tmp
            return False

        except socket.error as e:
            tmp.onerror.emit()
            raise

    @try_block
    def send_data(self, data: bytes):
        self.socket.sendall(data)
        pass

    @try_block
    def send_file(self, filepath):
        with open(filepath, "rb") as file:
            self.socket.sendfile(file)
        pass

    @try_block
    def shutdown(self):
        self.socket.shutdown(1)
