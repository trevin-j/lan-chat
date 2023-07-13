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
from netifaces import interfaces, ifaddresses, AF_INET
import sys
import time
from crypto import get_n_and_g, get_private_key, diffie_first_step, diffie_second_step

from lcsocket import LCSocket

DEFAULT_PORT = 29001

BROADCAST_PACKET = "lan-chat-find"
BROADCAST_RESPONSE = "lan-chat-found-"

class NoMoreClients(Exception):
    pass


def get_ip_addresses() -> List[str]:
    addresses = []
    for interface in interfaces():
        interface_addresses = ifaddresses(interface)
        if AF_INET in interface_addresses.keys():
            for address in interface_addresses[AF_INET]:
                if "addr" in address.keys():
                    addresses.append(address["addr"])
    return addresses


def reply_to_broadcasts(name: str, server: Server):

    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(("", DEFAULT_PORT))
    udp_socket.settimeout(0.2)
    while True:
        try:
            data, addr = udp_socket.recvfrom(4096)
            if data.decode() == BROADCAST_PACKET:
                udp_socket.sendto(f"{BROADCAST_RESPONSE}{name}".encode(), addr)
        except (TimeoutError, socket.timeout):
            if server.is_done():
                udp_socket.close()
                return


class ClientConnection(Thread):
    def __init__(self, id: int, sock: LCSocket, q: Queue[Tuple[Dict[str, str], ClientConnection]]) -> None:
        """
        Initialize.
        q: The queue to put received messages on.
        """
        super().__init__()
        self._id = id
        self._sock = sock
        self._sock.settimeout(0.2)
        self._q = q
        self._name = ""
        self._stopped = False

    def is_ready(self) -> bool:
        return self._name != ""

    def run(self):
        global client_threads_alive
        while not self._stopped:
            try:
                self._q.put((self._sock.full_receive(), self))
            except (TimeoutError, socket.timeout):
                continue
            except OSError as e:
                if self._stopped:
                    break
                else:
                    print("ERR:", e, str(e))
        

    def set_name(self, name: str) -> None:
        self._name = name

    def get_name(self) -> str:
        return f"#{self._id}:{self._name}"
    
    def send(self, packet: Dict[str, str]) -> None:
        self._sock.full_send(packet)

    def get_id(self) -> int:
        return self._id

    def disconnect(self, msg: str = "You disconnected from the server. Press enter to exit.") -> None:
        self._stopped = True
        self.send({"action": "DISCONNECT", "message": msg, "source": "SERVER"})
        self._sock.close()

    

class Server(Thread):
    def __init__(self, name):
        """ Initialize. """
        super().__init__()

        self._n, self._g = get_n_and_g()
        self._private_key = get_private_key(self._n)
        # Calculate our partial key
        self._partial_key = diffie_first_step(self._private_key, self._n, self._g)

        self._q: Queue[Tuple[Dict[str, str], ClientConnection]] = Queue()
        self._clients: List[ClientConnection] = []

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self._sock.bind(("", DEFAULT_PORT))
        except OSError:
            print("The port for this application is already in use or wasn't properly freed last time.")
            print("Would you like to wait until it's available? (y/n)")
            if input("> ") == "y":
                num_dots = 0
                success = False
                while not success:
                    print("\033[2K\033[0EWaiting" + "." * num_dots + "\033[0E", end="", flush=True)
                    num_dots = (num_dots + 1) % 4
                    try:
                        self._sock.bind(("", DEFAULT_PORT))
                        success = True
                    except OSError:
                        time.sleep(0.15)
                print("\033[2K\033[0EPort acquired.")
                time.sleep(3)
            else:
                sys.exit()

        self._sock.listen(1)
        self._sock.settimeout(0.2)

        self._next_client_id = 0

        self._replier_thread = None

        self._ips = get_ip_addresses()

        self._host_name = name

        self._done = False

    def run(self):
        """ Run the thread. """
        connections_thread = ConnectionGetter(self, self._n, self._g, self._private_key, self._partial_key)
        connections_thread.start()

        while True:
            packet, sender = self._recv()
            try:
                self._handle_packet(packet, sender)
            except NoMoreClients:
                self._done = True
                connections_thread.stop()
                connections_thread.join()
                if self._replier_thread is not None:
                    self._replier_thread.join()
                return
            
    def is_done(self) -> bool:
        return self._done

    def make_visible(self):
        self._replier_thread = Thread(target=reply_to_broadcasts, args=(self._host_name, self))
        self._replier_thread.start()

    def _info_msg(self, sender: ClientConnection) -> str:
        msg =   "Server info:\n"
        msg +=  "         ---------------------\n"
        msg += f"         Server name: {self._host_name}\n"
        msg += f"         Server IPs: {', '.join(self._ips)}\n"
        msg += f"         Host: {self._clients[0].get_name()}\n"
        msg += f"         Connected users: {len(self._clients)}\n"
        for client in self._clients:
            msg += f"           {client.get_name()}\n"
        msg += f"         Your username is {sender.get_name()}"
        return msg
    
    def _help_msg(self) -> str:
        return \
         """Help menu:
         -----------------
         /info - receive server info
         /h /help - display help menu
         /q /quit - disconnect
         /kick {id} - kick the player with the id
         /ban {id} - bans the player with the id by blacklisting their ip address"""
    
    def _disconnect_client(self, client_id: int) -> bool:
        disconnected = False
        for client in reversed(self._clients):
            if client.get_id() == client_id or client_id == 0:
                client.disconnect()
                client.join()
                self._clients.remove(client)
                self._send_all_clients({"action": "MESSAGE", "message": f"{client.get_name()} disconnected.", "source": "SERVER"})
                if len(self._clients) == 0:
                    raise NoMoreClients
                disconnected = True
        return disconnected
                

    def _handle_command(self, sender: ClientConnection, cmd: str) -> None:
        msg = ""
        if cmd == "info":
            msg = self._info_msg(sender)
        elif cmd == "help" or cmd == "h":
            msg = self._help_msg()
        elif cmd in ("q", "quit"):
            self._disconnect_client(sender.get_id())
            return
        else:
            sender.send({"action": "ERROR", "message": f"ERR 3: UNKNOWN COMMAND: /{cmd}", "source": "SERVER"})
            return

        sender.send({"action": "MESSAGE", "message": msg, "source": "SERVER"})


    def _handle_packet(self, packet: Dict[str, str], sender: ClientConnection) -> None:
        try:
            action = packet["action"]
            msg = packet["message"]

        except KeyError:
            return
        
        if action == "MESSAGE":
            if not sender.is_ready():
                sender.send({"action": "ERROR", "message": "ERR 1: CANNOT SEND MESSAGE BEFORE FULLY CONNECTED", "source": "SERVER"})
                return
            if msg[0] == "/" or msg[0] == "\\":
                self._handle_command(sender, msg[1:])
                return
            self._send_all_clients({"action": "MESSAGE", "message": msg, "source": sender.get_name()})
            return
        
        if action == "CONNECT":
            if msg == "":
                sender.send({"action": "ERROR", "message": "ERR 2: NAME CANNOT BE BLANK", "source": "SERVER"})
                return
            sender.set_name(msg)
            self._send_all_clients({"action": "MESSAGE", "message": f"{sender.get_name()} has joined.", "source": "SERVER"})
            return

        
    def _send_all_clients(self, packet: Dict[str, str]) -> None:
        for client in self._clients:
            client.send(packet)

    def _recv(self) -> Tuple[Dict[str, str], ClientConnection]:
        return self._q.get()
    
    def accept(self) -> Tuple[str, Tuple[str, int]]:
        return self._sock.accept()
    
    def add_client(self, lcsock: LCSocket) -> None:
        self._clients.append(ClientConnection(self._next_client_id, lcsock, self._q))
        self._next_client_id += 1
        self._clients[-1].start()


# Thread to get new connections
class ConnectionGetter(Thread):
    def __init__(self, server: Server, n: int, g: int, secret_key: int, partial_key: int) -> None:
        super().__init__()
        self._stopped = False
        self._server = server

        self._n = n
        self._g = g
        self._secret_key = secret_key
        self._partial_key = partial_key

    def stop(self) -> None:
        self._stopped = True

    def run(self) -> None:
        while not self._stopped:
            try:
                client_sock, addr = self._server.accept()
                lcsock = LCSocket(client_sock)
                # lcsock.setup_encryption()
                self.setup_encryption(lcsock)
                self._server.add_client(lcsock)
            except (TimeoutError, socket.timeout):
                continue
            except ValueError:
                lcsock.close()
                continue

    def setup_encryption(self, lcsock: LCSocket) -> None:
        """
        Communicate with client to set up e2e encryption.
        Server sends encryption data packet to client
        Client sends one back
        """
        # Inform client of n and g and our partial key
        lcsock.full_send({"action": "SETUP_ENCRYPTION", "message": f"{self._n},{self._g},{self._partial_key}", "source": "SERVER"})
        # Receive client's partial key
        pack = lcsock.full_receive()
        if pack["action"] != "SETUP_ENCRYPTION":
            raise ValueError
        other_partial = int(pack["message"])
        
        symmetrical_key = diffie_second_step(other_partial, self._secret_key, self._n)

        lcsock.set_encryption_key(symmetrical_key)
