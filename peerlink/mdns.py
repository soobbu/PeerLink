from typing import List

from peerlink.utils import Signal
from zeroconf import ServiceInfo, ServiceListener, Zeroconf


class Listener(ServiceListener):
    def __init__(self) -> None:
        super().__init__()
        self.onadd = Signal("servicename", "addresses", "port")
        self.onremove = Signal("servicename")

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        print(f"Service {name} updated")

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        self.onremove.emit(name.removesuffix(f".{type_}"))
        print(f"Service {name} removed")

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        service = self.get_info(zc, type_, name)
        if service:
            self.onadd.emit(service.name.removesuffix(f".{type_}"), service.addresses, service.port)
            print(
                f"Service {name} added, service addr: {service.parsed_addresses()}:{service.port}"
            )

    def get_info(self, zc: Zeroconf, type_, name):
        return zc.get_service_info(type_, name)


class MultiDNS:
    mdns = Zeroconf()
    listener = Listener()
    service_info = None

    @classmethod
    def register_service(cls, name: str, port: int, addresses: List[bytes]) -> None:
        cls.service_info = ServiceInfo(
            type_="_p2p._tcp.local.",
            name=f"{name}._p2p._tcp.local.",
            port=port,
            addresses=addresses,
        )
        cls.mdns.register_service(cls.service_info)
        pass

    @classmethod
    def service_listener(cls) -> None:
        cls.mdns.add_service_listener("_p2p._tcp.local.", cls.listener)
        pass

    @classmethod
    def unregister(cls):
        if cls.service_info:
            cls.mdns.unregister_service(cls.service_info)
        cls.mdns.remove_all_service_listeners()

    @classmethod
    def service_exists(cls, name):
        if cls.mdns.get_service_info(
            type_="_p2p._tcp.local.", name=f"{name}._p2p._tcp.local."
        ):
            return True
        else:
            return False

    @classmethod
    def shutdown(cls):
        cls.unregister()
        cls.mdns.close()

