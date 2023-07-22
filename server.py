"""
This module holds the server-side code of the P2P application.
"""

from __future__ import annotations
from typing import List, Tuple, Dict
import socket
from threading import Thread
from queue import Queue
import time
import sys

import netifaces

from crypto import get_n_and_g, get_private_key, diffie_first_step, diffie_second_step
from lcsocket import LCSocket

DEFAULT_PORT = 29001

BROADCAST_PACKET = "lan-chat-find"
BROADCAST_RESPONSE = "lan-chat-found-"

class NoMoreClients(Exception):
    """
    Extremely simple exception to raise when the server has no more clients.
    """


def get_ip_addresses() -> List[str]:
    """
    Get a list of IP addresses that this host has.
    """
    addresses = []
    for interface in netifaces.interfaces():
        interface_addresses = netifaces.ifaddresses(interface)
        if netifaces.AF_INET in interface_addresses.keys():
            for address in interface_addresses[netifaces.AF_INET]:
                if "addr" in address.keys():
                    addresses.append(address["addr"])
    return addresses


def reply_to_broadcasts(name: str, server: Server):
    """
    A function to be started as a thread which responds to UDP broadcasts
    to inform of this host and address.
    """
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
    """
    A class to represent a connection to a client which operates as its own thread.
    """
    def __init__(
            self,
            client_id: int,
            sock: LCSocket,
            q: Queue[Tuple[Dict[str, str], ClientConnection]]
        ) -> None:
        """
        Initialize.
        q: The queue to put received messages on.
        """
        super().__init__()
        self._client_id = client_id
        self._sock = sock
        self._sock.settimeout(0.2)
        self._q = q
        self._name = ""
        self._stopped = False
        self._connected = True


    def is_ready(self) -> bool:
        """
        Check if the client is ready to be used.
        """
        return self._name != ""


    def run(self):
        """
        Run the thread.
        """
        while not self._stopped:
            try:
                self._q.put((self._sock.full_receive(), self))
            except (TimeoutError, socket.timeout):
                continue
            except OSError as error:
                if self._stopped:
                    break
                print("ERR:", error, str(error))
            except AttributeError:
                # Trying to decrypt when disconnected yields attributeerror. So, disconnect.
                self._q.put(({"action": "MESSAGE", "message": "/q", "source": "CLIENT"}, self))
                self._connected = False


    def set_name(self, name: str) -> None:
        """
        Set the client name.
        """
        self._name = name


    def get_name(self) -> str:
        """
        Get the client name in form "#{id}:{name}"
        """
        return f"#{self._client_id}:{self._name}"


    def send(self, packet: Dict[str, str]) -> None:
        """
        Send a packet to this client.
        """
        try:
            self._sock.full_send(packet)
        except BrokenPipeError:
            # Trick server into seeing client disconnecting
            self._q.put(({"action": "MESSAGE", "message": "/q", "source": "CLIENT"}, self))
            self._connected = False


    def get_id(self) -> int:
        """
        Get the ID of this client.
        """
        return self._client_id


    def disconnect(self, msg: str) -> None:
        """
        Disconnect from the server. Send the specified message to the client.
        """
        self._stopped = True
        if self._connected:
            self.send({"action": "DISCONNECT", "message": msg, "source": "SERVER"})
        self._sock.close()


class Server(Thread):
    """
    A class representing the server. Runs as its own thread.
    """
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
            print("The port for this application is already in use or wasn't properly freed.")
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


    def run(self) -> None:
        """
        Run the thread.
        """
        connections_thread = ConnectionGetter(
            self,
            self._n,
            self._g,
            self._private_key,
            self._partial_key
        )
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
        """
        Check if the server is done.
        """
        return self._done


    def make_visible(self):
        """
        Start the thread that responds to broadcasts,
        thus making this host "visible" on the LAN.
        """
        self._replier_thread = Thread(target=reply_to_broadcasts, args=(self._host_name, self))
        self._replier_thread.start()


    def _info_msg(self, sender: ClientConnection) -> str:
        """
        Get the server info message.
        """
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
        """
        Get the chat command help message.
        """
        return \
         """Help menu:
         -----------------
         /info - receive server info
         /h /help - display help menu
         /q /quit - disconnect
         /kick {id} - kick the player with the id"""
        #  /ban {id} - bans the player with the id by blacklisting their ip address"""


    def _disconnect_client(self, client_id: int, disconnect_type: str="disconnect") -> bool:
        """
        Disconnect the client based on its ID.
        client_id: the id of the client to disconnect.
        disconnect_type: "disconnect", "kick" - the type of disconnect
        returns True if successfully disconnected
        """
        disconnected = False

        msg = "{0} disconnected."
        client_msg = "You have disconnected. Press enter to quit."

        # Generate message. {0} represents the client name
        if disconnect_type == "kick":
            msg = "{0} was kicked."
            client_msg = "You were kicked from the room. Press enter to quit."

        for client in reversed(self._clients):
            if client.get_id() == client_id or client_id == 0:
                client.disconnect(client_msg)
                client.join()
                self._clients.remove(client)
                self._send_all_clients({
                    "action": "MESSAGE",
                    "message": msg.format(client.get_name()),
                    "source": "SERVER"
                })
                if len(self._clients) == 0:
                    raise NoMoreClients
                disconnected = True
        return disconnected


    def _handle_command(self, sender: ClientConnection, cmd: str) -> None:
        """
        Handle the command that the user sent.
        """
        msg = ""
        split_cmd = cmd.split()
        if len(split_cmd) == 0:
            return
        if cmd == "info":
            msg = self._info_msg(sender)
        elif cmd == "help" or cmd == "h":
            msg = self._help_msg()
        elif cmd in ("q", "quit"):
            self._disconnect_client(sender.get_id())
            return
        elif split_cmd[0] == "kick":
            if sender.get_id() != 0:
                sender.send({
                    "action": "ERROR",
                    "message": "ERR 7: ONLY HOST CAN KICK",
                    "source": "SERVER"
                })
                return
            if len(split_cmd) < 2:
                sender.send({
                    "action": "ERROR",
                    "message": "ERR 4: MISSING COMMAND TARGET",
                    "source": "SERVER"
                })
                return
            if not split_cmd[1].isdigit():
                sender.send({
                    "action": "ERROR",
                    "message": "ERR 6: TARGET MUST BE INTEGER",
                    "source": "SERVER"
                })
                return
            if split_cmd[1] == "0":
                sender.send({
                    "action": "ERROR",
                    "message": "ERR 8: CANNOT KICK HOST",
                    "source": "SERVER"
                })
                return
            success = self._disconnect_client(int(split_cmd[1]), "kick")
            if not success:
                sender.send({
                    "action": "ERROR",
                    "message": "ERR 5: COMMAND TARGET DOES NOT EXIST",
                    "source": "SERVER"
                })
            return
        else:
            sender.send({
                "action": "ERROR",
                "message": f"ERR 3: UNKNOWN COMMAND: /{cmd}",
                "source": "SERVER"
            })
            return

        sender.send({"action": "MESSAGE", "message": msg, "source": "SERVER"})


    def _handle_packet(self, packet: Dict[str, str], sender: ClientConnection) -> None:
        """
        Handle a packet sent by the client.
        """
        try:
            action = packet["action"]
            msg = packet["message"]

        except KeyError:
            return

        if action == "MESSAGE":
            if not sender.is_ready():
                sender.send({
                    "action": "ERROR",
                    "message": "ERR 1: CANNOT SEND MESSAGE BEFORE FULLY CONNECTED",
                    "source": "SERVER"
                })
                return
            if msg[0] == "/" or msg[0] == "\\":
                self._handle_command(sender, msg[1:])
                return
            self._send_all_clients({
                "action": "MESSAGE",
                "message": msg,
                "source": sender.get_name()
            })
            return

        if action == "CONNECT":
            if msg == "":
                sender.send({
                    "action": "ERROR",
                    "message": "ERR 2: NAME CANNOT BE BLANK",
                    "source": "SERVER"
                })
                return

            sender.set_name(msg)
            self._send_all_clients({
                "action": "MESSAGE",
                "message": f"{sender.get_name()} has joined.",
                "source": "SERVER"
            })
            return


    def _send_all_clients(self, packet: Dict[str, str]) -> None:
        """
        Send the packet to all clients.
        """
        for client in self._clients:
            client.send(packet)


    def _recv(self) -> Tuple[Dict[str, str], ClientConnection]:
        """
        Receive the next queued packet.
        """
        return self._q.get()


    def accept(self) -> Tuple[str, Tuple[str, int]]:
        """
        Accept a client.
        """
        return self._sock.accept()


    def add_client(self, lcsock: LCSocket) -> None:
        """
        Add a client to the server to manage.
        """
        self._clients.append(ClientConnection(self._next_client_id, lcsock, self._q))
        self._next_client_id += 1
        self._clients[-1].start()


class ConnectionGetter(Thread):
    """
    A thread to receive clients and initialize the encryption.
    """
    def __init__(self, server: Server, n: int, g: int, secret_key: int, partial_key: int) -> None:
        super().__init__()
        self._stopped = False
        self._server = server

        self._n = n
        self._g = g
        self._secret_key = secret_key
        self._partial_key = partial_key


    def stop(self) -> None:
        """
        Stop this thread.
        """
        self._stopped = True


    def run(self) -> None:
        """
        Run the thread.
        """
        while not self._stopped:
            try:
                client_sock, _addr = self._server.accept()
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
        try:
            lcsock.full_send({
                "action": "SETUP_ENCRYPTION",
                "message": f"{self._n},{self._g},{self._partial_key}",
                "source": "SERVER"
            })
        except BrokenPipeError:
            lcsock.close()
            return
        # Receive client's partial key
        pack = lcsock.full_receive()
        if pack["action"] != "SETUP_ENCRYPTION":
            raise ValueError
        other_partial = int(pack["message"])

        symmetrical_key = diffie_second_step(other_partial, self._secret_key, self._n)

        lcsock.set_encryption_key(symmetrical_key)
