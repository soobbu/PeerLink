import sys
from random import randrange

from peerlink.model import Model
from peerlink.ui import (ChatWindow, ConnectionWindow, Controller, LoginWindow,
                         QApplication)

app = QApplication(sys.argv)
login = LoginWindow()
conn =ConnectionWindow()
chat = ChatWindow()
window = Controller(login, conn, chat, Model(randrange(8000,9000,1)))
login.show()
app.exec()
