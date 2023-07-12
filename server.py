"""

A packet looks like the following:
{
    "action": {action},             -- options: CONNECT, DISCONNECT, ERROR, MESSAGE, FIND
    "message": {message},           -- On ERROR, it is a reason, on MESSAGE it is the msg.
    "source": {sender name}
}

A packet must have all the fields, even if they are just empty. Otherwise, the packet will be ignored.

In sending and receiving packets, each packet is separated by 2 CRLF.

On connection, client should send connect packet with message as their name.
Server will then send a connect packet with the message as the other client's name.

On disconnect, server sends disconnect packet with message as name of client who disconnected.

"""

from __future__ import annotations
from threading import Thread
from typing import List, Tuple, Dict
from queue import Queue
import socket
from debugprint import sprint

from lcsocket import LCSocket

DEFAULT_PORT = 29001

BROADCAST_PACKET = "lan-chat-find"
BROADCAST_RESPONSE = "lan-chat-found-"

def reply_to_broadcasts(name: str):

    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(("", DEFAULT_PORT))

    while True:
        data, addr = udp_socket.recvfrom(4096)
        if data.decode() == BROADCAST_PACKET:
            udp_socket.sendto(f"{BROADCAST_RESPONSE}{name}".encode(), addr)



class ClientConnection(Thread):
    def __init__(self, id: int, sock: LCSocket, q: Queue[Tuple[Dict[str, str], ClientConnection]]) -> None:
        """
        Initialize.
        q: The queue to put received messages on.
        """
        super().__init__()
        self._id = id
        self._sock: LCSocket = sock
        self._q = q
        self._name = ""

    def is_ready(self) -> bool:
        return self._name != ""

    def run(self):
        while True:
            self._q.put((self._sock.full_receive(), self))

    def set_name(self, name: str) -> None:
        self._name = name

    def get_name(self) -> str:
        return self._name
    
    def send(self, packet: Dict[str, str]) -> None:
        self._sock.full_send(packet)
    

class Server(Thread):
    def __init__(self, name):
        """ Initialize. """
        super().__init__()
        self._q: Queue[Tuple[Dict[str, str], ClientConnection]] = Queue()
        self._clients: List[ClientConnection] = []

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.bind(("", DEFAULT_PORT))
        self._sock.listen(1)

        self._host_name = name

    def run(self):
        """ Run the thread. """
        self._get_connections()

        while True:
            packet, sender = self._recv()
            self._handle_packet(packet, sender)

    def make_visible(self):
        replier_thread = Thread(target=reply_to_broadcasts, args=(self._host_name,))
        replier_thread.start()

    def _handle_packet(self, packet: Dict[str, str], sender: ClientConnection) -> None:
        sprint(packet, sender.get_name())
        try:
            action = packet["action"]
            msg = packet["message"]

        except KeyError:
            return
        
        if action == "MESSAGE":
            if not sender.is_ready():
                sender.send({"action": "ERROR", "message": "1: CANNOT SEND MESSAGE BEFORE FULLY CONNECTED", "source": "SERVER"})
                return
            self._send_all_clients({"action": "MESSAGE", "message": msg, "source": sender.get_name()})
            return
        
        if action == "CONNECT":
            if msg == "":
                sender.send({"action": "ERROR", "message": "2: NAME CANNOT BE BLANK", "source": "SERVER"})
                return
            sender.set_name(msg)
            return

        
    def _send_all_clients(self, packet: Dict[str, str]) -> None:
        for client in self._clients:
            client.send(packet)

    def _recv(self) -> Tuple[Dict[str, str], ClientConnection]:
        return self._q.get()

    def _get_connections(self) -> None:
        # Waiting on clients to join
        client1_sock, ip1 = self._sock.accept()
        client2_sock, ip2 = self._sock.accept()
        self._clients.append(ClientConnection(0, LCSocket(client1_sock), self._q))
        self._clients.append(ClientConnection(1, LCSocket(client2_sock), self._q))
        for client in self._clients:
            client.start()


