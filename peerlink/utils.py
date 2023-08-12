import json
import sys
from inspect import getfullargspec
from mimetypes import guess_type
from os.path import abspath, getsize, join
from time import time
from uuid import UUID, uuid4


class Signal:
    def __init__(self, *args) -> None:
        self.slots = []
        self.args = list(args)

    def connect(self, slot):
        argspec = getfullargspec(slot)
        if "self" in argspec.args:
            argspec.args.remove("self")
        if "cls" in argspec.args:
            argspec.args.remove("cls")
        if self.args != argspec.args:
            raise ValueError(f"Invalid Params/Arguments - {self.args}, {argspec.args}")
        if not slot in self.slots:
            self.slots.append(slot)

    def emit(self, *args, **kwargs):
        if self.args and not args:
            raise ValueError("Params registered but not emitted.")
        elif not self.args and args:
            raise ValueError("Params not registered but attempted to emit.")
        for slot in self.slots:
            slot(*args, **kwargs)

    def disconnect(self, slot):
        if slot in self.slots:
            self.slots.remove(slot)
        else:
            raise IndexError("Slot isnt connected to signal.")

    def disconnectall(self):
        for slot in self.slots:
            self.disconnect(slot)


class MsgFormat(dict):
    def __init__(cls, **kwargs):
        kwargs["time"] = time()
        super().__init__(**kwargs)

    @classmethod
    def text(cls, text_: str):
        return cls(text=text_)

    @classmethod
    def file(cls, filepath: str):
        return cls(
            filename=filepath.split("/")[-1],
            type=guess_type(filepath),
            size=getsize(filepath),
        )

    @classmethod
    def query_req(cls, name, uuid, ip, port):
        return cls(query="req", name=name, uuid=uuid, ip=ip, port=port)

    @classmethod
    def query_shut(cls):
        return cls(query="shut")

    @classmethod
    def query_acpt(cls, name, uuid, ip, port):
        return cls(query="acp", name=name, uuid=uuid, ip=ip, port=port)

    def pack(self):
        return json.dumps(self).encode("utf-8")

    @staticmethod
    def unpack(bytes_) -> dict:
        try:
            return json.loads(bytes_)
        except json.JSONDecodeError:
            print(str(bytes_, encoding="utf-8"))
            raise


class Peer:
    def __init__(self, username: str) -> None:
        self.username = username
        self.uuid: UUID = uuid4()
        self.priv_key: bytes
        self.pub_key: bytes

    def get_uuid(self) -> str:
        return str(self.uuid).replace("-", "")

    def gen_priv_key(self):
        pass

    def gen_pub_key(self):
        pass

def resource_path(relative_path) -> str:
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = abspath(".")

    return join(base_path, relative_path)