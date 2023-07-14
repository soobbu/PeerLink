from atexit import register as callonexit
from socket import inet_aton, inet_ntoa

from peerlink.mdns import MultiDNS
from peerlink.network import LOCAL_IP, Reciever, Sender
from noise.connection import NoiseConnection, NoiseInvalidMessage
from peerlink.ui import QSignal
from peerlink.utils import MsgFormat, Peer, Signal


class RequestReciver:
    def __init__(self, reciever: Reciever) -> None:
        self.onreqrecv = Signal('data')
        self.onreqacpt = Signal('data')
        self._reciever = reciever
        self._reciever.ondata.connect(self._read)


    def _read(self, data, sock):
        data = MsgFormat.unpack(data)
        data['sock'] = sock
        try:
            if data.get('query') == 'req':
                self.onreqrecv.emit(data)
            elif data.get('query') == 'acp':
                self.onreqacpt.emit(data)
        except KeyError:
            raise KeyError(f'Invalid data recived - {data}')

    def disable(self):
        self._reciever.ondata.disconnect(self._read)


class SecureConnection:
    def __init__(self, reciever : Reciever, sender : Sender , proto : NoiseConnection, initiator = False) -> None:
        self.reciever = reciever
        reciever.ondata.connect(self._read_payload)

        self.onconnsecure = Signal()
        self.proto = proto
        self.sender = sender

        if initiator:
            proto.set_as_initiator()
            proto.start_handshake()
            sender.send_data(proto.write_message())
        else:
            proto.set_as_responder()
            proto.start_handshake()


    
    def _read_payload(self, data, sock):
        self.proto.read_message(data)
        if not self.proto.handshake_finished:
            self.sender.send_data(self.proto.write_message())
            if self.proto.handshake_finished:
                self.onconnsecure.emit()
                self.reciever.ondata.disconnect(self._read_payload)
        else:
            self.onconnsecure.emit()
            self.reciever.ondata.disconnect(self._read_payload)

    def disable(self):
        self.reciever.ondata.disconnect(self._read_payload)

class ChatReciver:
    def __init__(self, reciever: Reciever, proto : NoiseConnection = None) -> None:
        self.ontext = Signal('data')
        self.onfile = Signal('data', 'finished')
        self.onshut = Signal()
        self._reciever = reciever
        self._reciever.ondata.connect(self._read)
        self._proto = proto
            
    
    def _read(self, data, sock):
        try:
            if self._proto:
                data = MsgFormat.unpack(self._proto.decrypt(data))
            else:
                data = MsgFormat.unpack(data)
        except NoiseInvalidMessage :
            raise 

        try:
            if isinstance(data, dict):
                if data.get('text'):
                    self.ontext.emit(data)
                elif data.get('filename'):
                    self.onfile.emit(data, False)
                    self._tmp_file = open(data.get('filename'), 'wb')
                    self._tmp_file_size = data.get('size')
                    self._reciever.ondata.disconnect(self._read)
                    self._reciever.ondata.connect(self._recv_file)
                elif data.get('query') == 'shut':
                    self._reciever.ondata.disconnect(self._read)
                    self.onshut.emit()
        except KeyError:
            raise KeyError(f'Invalid data recieved - {data}')

    def disable(self):
        self._reciever.ondata.disconnect(self._read)
    
    def _recv_file(self, data):
        self._tmp_file.write(data)
        self._tmp_file_size -= len(data)
        if self._tmp_file_size == 0:
            self._reciever.ondata.disconnect(self._recv_file)
            self._reciever.ondata.connect(self._read)
            self._tmp_file.close()
            self.onfile.emit(None, True)
        pass


class Model:
    def __init__(self, port=8080) -> None:
        callonexit(self.shutdown)
        self.sent_reqs = list()
        self.recv_reqs = list()
        self.receiver = Reciever(host=LOCAL_IP, port=port)
        self.mdns = MultiDNS()
        self.local_devices = list()
        self.connection = None
        self.state = None

        self._register_signals()

    def _register_signals(self):
        self.onreqrecv = QSignal(str, str, int)
        self.onreqacpt = QSignal(str, str, int)
        self.ondevicediscovery = QSignal(str, str, int)
        self.ondeviceloss = QSignal()
        self.ontext = QSignal(str, float)
        self.onfile = QSignal(str, float)
        self.onfilefinished = QSignal()
        self.ondisconnect = QSignal()
        self.onconnsecure = QSignal()

    def __set_chat_state(self):
        self.onconnsecure.emit()
        self.state = ChatReciver(self.receiver, self.proto)
        self.state.ontext.connect(self._read_text)
        self.state.onfile.connect(self._read_file)
        self.state.onshut.connect(self._connection_shutdown)
        self.local_devices.clear()
        self.mdns.unregister()


    def _secure_connection(self, initiator = False):
        self.state.disable()
        self.proto = NoiseConnection.from_name(b'Noise_NN_25519_ChaChaPoly_SHA256')
        if initiator:
            tmp = SecureConnection(self.receiver, self.connection, self.proto, True)
        else:
            tmp = SecureConnection(self.receiver, self.connection, self.proto)
        tmp.onconnsecure.connect(self.__set_chat_state)

            


    def _connection_shutdown(self):
        self.connection = None
        self.receiver.ondata.disconnectall()
        self.ondisconnect.emit()

    def _set_request_state(self):
        self.recv_reqs.clear()
        self.state = RequestReciver(self.receiver)
        self.state.onreqrecv.connect(self._req_recieved)
        self.state.onreqacpt.connect(self._req_accepted)
        self.mdns.register_service(self.peer.username, self.receiver.addr[1], [
            inet_aton(self.receiver.addr[0])])

        self.mdns.service_listener()
        self.mdns.listener.onadd.connect(self._new_local_service)
        self.mdns.listener.onremove.connect(self._remove_local_service)

    def _req_recieved(self, data):
        self.recv_reqs.append(data)
        self.onreqrecv.emit(data['name'], data['ip'], data['port'])

    def _req_accepted(self, data):
        for req in self.sent_reqs:
            if req['ip'] == data['ip']:
                self.receiver.disconnect_except(data['sock'])
                self.onreqacpt.emit(data['name'], data['ip'], data['port'])
                self.connection = req['sender']
                self._secure_connection(True)

    def _read_text(self, data):
        self.ontext.emit(data['text'], data['time'])

    def _read_file(self, data, finished):
        if finished and data is None:
            self.onfilefinished.emit()
        else:
            self.onfile.emit(data['filename'], data['time'])

    def set_username(self, username) -> bool:
        if not self.mdns.service_exists(username):
            self.receiver.start()
            self.peer = Peer(username)
            self._set_request_state()
            return True
        else:
            return False

    def _new_local_service(self, servicename: str, addresses, port):
        if not servicename == self.mdns.service_info.name.split('.')[0]:
            self.local_devices.append({'name': servicename,
                                       'ip': inet_ntoa(addresses[0]),
                                       'port': port})
            self.ondevicediscovery.emit(
                servicename, inet_ntoa(addresses[0]), port)

    def _remove_local_service(self, servicename):
        for device in self.local_devices:
            if device['name'] == servicename:
                self.local_devices.remove(device)
                self.ondeviceloss.emit()

    def send_req(self, host, port):
        obj = Sender.send_query(host, port, MsgFormat.query_req(
            self.peer.username, self.peer.get_uuid(), *self.receiver.addr).pack())
        self.sent_reqs.append({'ip': host, 'port': port, 'sender': obj})


    def accept_req(self, host, port):
        for req in self.recv_reqs:
            if req['port'] == port:
                self.connection = Sender.send_query(host, port,
                                                    MsgFormat.query_acpt(self.peer.username,
                                                                         self.peer.get_uuid(),
                                                                         *self.receiver.addr).pack())
                self.receiver.disconnect_except(req['sock'])
                self._secure_connection()
                self.onreqacpt.emit(req['name'], req['ip'], req['port'])

    def send_msg(self, text):
        self.connection.send_data(
            self.proto.encrypt(MsgFormat.text(text).pack())
            )

    def send_file(self, path):
        self.connection.send_data(self.proto.encrypt(MsgFormat.file(path).pack()))
        self.connection.send_file(path)

    def disconnect(self):
        if self.connection:
            self.connection.send_data(
                self.proto.encrypt(MsgFormat.query_shut().pack())
                )
            self.connection.shutdown()
            self.receiver.ondata.disconnectall()

    def disconnect_n_return(self):
        self.disconnect()
        self.connection = None
        self._set_request_state()

    def shutdown(self):
        self.disconnect()
        self.mdns.shutdown()

