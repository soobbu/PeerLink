from datetime import datetime
from functools import partial
from time import time

from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (QApplication, QFileDialog, QGridLayout,
                             QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                             QPushButton, QScrollArea, QTextEdit, QVBoxLayout,
                             QWidget)


# https://stackoverflow.com/questions/69594116/passing-generic-type-to-inner-class
# A modified version
class QSignal:
    def __init__(self, *args):
        Emitter = type("Emitter", (QObject,), {"signal": pyqtSignal(*args)})
        self.emitter = Emitter()

    def emit(self, *args, **kw):
        self.emitter.signal.emit(*args, **kw)

    def connect(self, slot):
        self.emitter.signal.connect(slot)


class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(200, 250)
        self.setWindowTitle("P2P Chat - Join")

        root_layout = QVBoxLayout()

        self.label = QLabel("")
        self.label.setPixmap(QPixmap("icons/user_big.png"))
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.username = QLineEdit()
        self.username.setPlaceholderText("Enter Username")

        self.proceed_btn = QPushButton(QIcon("icons/proceed.png"), "Proceed")

        root_layout.addWidget(self.label)
        root_layout.addWidget(self.username)
        root_layout.addWidget(self.proceed_btn)

        self.setLayout(root_layout)


class ConnectionWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(280, 350)
        self.setWindowTitle("P2P Chat - Connection")

        root_layout = QVBoxLayout()
        h_layout = QHBoxLayout()

        self.label = QLabel("Available Peers :")
        self.reload_btn = QPushButton(QIcon("icons/reload.png"), "")

        self.peer_list_area = QScrollArea()
        self.peer_list_widget = QWidget()
        self.peer_list_layout = QGridLayout(self.peer_list_widget)
        self.peer_list_area.setWidgetResizable(True)
        self.peer_list_area.setWidget(self.peer_list_widget)

        self.req_label = QLabel("Incoming Requests :")
        self.req_list_area = QScrollArea()
        self.req_list_container = QWidget()
        self.req_list_layout = QGridLayout(self.req_list_container)
        self.req_list_area.setWidgetResizable(True)
        self.req_list_area.setWidget(self.req_list_container)

        h_layout.addWidget(self.label)
        h_layout.addWidget(self.reload_btn)
        root_layout.addLayout(h_layout)
        root_layout.addWidget(self.peer_list_area)
        root_layout.addWidget(self.req_label)
        root_layout.addWidget(self.req_list_area)

        self.setLayout(root_layout)


class ChatWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(330, 350)
        self.setWindowTitle("P2P Chat - Chat")

        root_layout = QVBoxLayout()
        v1_layout = QHBoxLayout()
        v2_layout = QHBoxLayout()

        self.conn_label = QLabel("Connected to : ")
        self.disconnect_btn = QPushButton("Disconnect")

        self.chat_widget = QTextEdit()
        self.chat_widget.ensureCursorVisible()
        self.chat_widget.setAcceptRichText(True)
        self.chat_widget.setReadOnly(True)
        self.chat_widget.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction
        )

        self.files_btn = QPushButton(QIcon("icons/upload.png"), "")
        self.chat_text = QLineEdit()
        self.send_btn = QPushButton("send")
        self.send_btn.setShortcut("Return")

        v1_layout.addWidget(self.conn_label)
        v1_layout.addWidget(self.disconnect_btn)

        v2_layout.addWidget(self.files_btn)
        v2_layout.addWidget(self.chat_text)
        v2_layout.addWidget(self.send_btn)

        root_layout.addLayout(v1_layout)
        root_layout.addWidget(self.chat_widget)
        root_layout.addLayout(v2_layout)

        self.setLayout(root_layout)


class Controller(QObject):
    def __init__(
        self,
        login_win: LoginWindow,
        conn_win: ConnectionWindow,
        chat_win: ChatWindow,
        model=None,
    ):
        super().__init__()
        self.login_ui = login_win
        self.conn_ui = conn_win
        self.chat_ui = chat_win
        self.model = model
        self._bind_btn()
        self._bind_callback()

    def _bind_btn(self):
        self.login_ui.proceed_btn.clicked.connect(self._validate)
        self.conn_ui.reload_btn.clicked.connect(self._reload)
        self.chat_ui.send_btn.clicked.connect(self._send_msg)
        self.chat_ui.files_btn.clicked.connect(self._send_file)
        self.chat_ui.disconnect_btn.clicked.connect(self._disconnect)

    def _bind_callback(self):
        self.login_ui.closeEvent = self.shutdown
        self.conn_ui.closeEvent = self.shutdown
        self.chat_ui.closeEvent = self.shutdown
        self.model.onreqacpt.connect(self._accept_req)
        self.model.onreqrecv.connect(self.new_req)
        self.model.ondevicediscovery.connect(self.new_peer)
        self.model.ondeviceloss.connect(self._reload)
        self.model.ontext.connect(self._recv_text)
        self.model.onfile.connect(self._recv_file)
        self.model.onfilefinished.connect(self._file_recved)
        self.model.ondisconnect.connect(self._remote_disconnect)
        self.model.onconnsecure.connect(self._conn_secured)

    def new_peer(self, name, host, port):
        self._add_to_grid(
            self.conn_ui.peer_list_layout,
            name,
            "icons/add.png",
            partial(self.model.send_req, host, port),
        )

    def new_req(self, name, host, port):
        self._add_to_grid(
            self.conn_ui.req_list_layout,
            name,
            "icons/accept.png",
            partial(self.model.accept_req, host, port),
        )

    def shutdown(self, event):
        self.model.shutdown()
        event.accept()

    def _recv_text(self, text, time):
        self.chat_ui.chat_widget.append(f"{self._posix_to_datetime(time)} - {text}")
        self.chat_ui.chat_widget.setAlignment(Qt.AlignmentFlag.AlignLeft)

    def _conn_secured(self):
        self._chat_print_info("Connection is secured.")

    def _chat_print_info(self, text):
        self.chat_ui.chat_widget.append(text)
        self.chat_ui.chat_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def _switch_btn_state(self, *args, disable=True):
        for btn in args:
            if disable:
                btn.setDisabled(True)
            else:
                btn.setDisabled(False)

    def _reload(self):
        self._refill_grid(
            self.conn_ui.peer_list_layout, self.model.local_devices, self.new_peer
        )

    def _recv_file(self, filename, time):
        self._switch_btn_state(self.chat_ui.send_btn, self.chat_ui.files_btn)
        self._chat_print_info(f"Receiving file {filename}")

    def _file_recved(self):
        self._switch_btn_state(
            self.chat_ui.send_btn, self.chat_ui.files_btn, disable=False
        )
        self._chat_print_info(f"File received")

    def _remote_disconnect(self):
        self._chat_print_info("Connection shutdown by remote peer.")
        self._switch_btn_state(self.chat_ui.send_btn, self.chat_ui.files_btn)

    def _refill_grid(self, grid, item_list, add_func):
        for i in range(grid.count()):
            grid.itemAt(i).widget().deleteLater()

        for i in item_list:
            add_func(i["name"], i["ip"], i["port"])

    def _posix_to_datetime(self, time):
        time = datetime.fromtimestamp(time)

        return time.strftime("%I:%M %p").lstrip("0")

    def _validate(self):
        if not self.login_ui.username.text().strip() == "":
            self.username = self.login_ui.username.text()
            self.login_ui.proceed_btn.setCursor(Qt.CursorShape.WaitCursor)
            if self.model.set_username(self.username):
                self.conn_ui.move(self.login_ui.pos())

                self.conn_ui.show()
                self.login_ui.destroy()
            else:
                QMessageBox.critical(
                    self.login_ui,
                    "Error",
                    "Device with same username already exists in network.",
                )
        else:
            QMessageBox.critical(self.login_ui, "Error", "Enter valid username.")

    def _send_msg(self):
        if not self.chat_ui.chat_text.text().strip() == "":
            msg = self.chat_ui.chat_text.text()
            self.chat_ui.chat_text.clear()

            self.chat_ui.chat_widget.append(
                f"{msg} - {self._posix_to_datetime(time())}"
            )
            self.chat_ui.chat_widget.setAlignment(Qt.AlignmentFlag.AlignRight)

            self.chat_ui.chat_widget.verticalScrollBar().setValue(
                self.chat_ui.chat_widget.verticalScrollBar().maximum()
            )

            self.model.send_msg(msg)
            pass

    def _send_file(self):
        filepath, type_ = QFileDialog.getOpenFileName(self.chat_ui, "Send File")
        if not filepath == '':
            self._chat_print_info(f"Sending file - {filepath}")
            self._switch_btn_state(self.chat_ui.send_btn, self.chat_ui.files_btn)
            self.model.send_file(filepath)
            self._switch_btn_state(self.chat_ui.send_btn, self.chat_ui.files_btn, disable=False)

        pass

    def _accept_req(self, name, ip, port):
        self.chat_ui.conn_label.setText(f"Connected to : {name} ({ip}:{port})")

        self.chat_ui.move(self.conn_ui.pos())
        self.chat_ui.chat_widget.clear()
        self._switch_btn_state(
            self.chat_ui.send_btn, self.chat_ui.files_btn, disable=False
        )
        self.chat_ui.show()
        self.conn_ui.hide()

    def _disconnect(self):
        self.model.disconnect_n_return()
        self.chat_ui.hide()
        self._reload()
        self._refill_grid(
            self.conn_ui.req_list_layout, self.model.recv_reqs, self.new_req
        )
        self.conn_ui.show()
        pass

    def _add_to_grid(self, grid: QGridLayout, label: str, icon: str, callback):
        btn = QPushButton(QIcon(icon), "")
        btn.setFixedSize(30, 30)
        btn.clicked.connect(callback)
        grid.addWidget(QLabel(label), grid.rowCount(), 0)
        grid.addWidget(btn, grid.rowCount() - 1, 1)
