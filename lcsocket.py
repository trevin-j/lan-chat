from typing import Dict
import socket
import json


CRLF = "\r\n"
SEPARATOR = CRLF*2
ENCODING = "utf-8"

class LCSocket:
    def __init__(self, sock: socket.socket) -> None:
        self._msg_q = []
        self._partial_packet = ""
        self._sock: socket.socket = sock

    def full_send(self, data: Dict[str, str]) -> None:
        """
        Send a full packet.
        """
        self._sock.sendall((json.dumps(data) + SEPARATOR).encode(ENCODING))

    def full_receive(self) -> Dict[str, str]:
        """
        Receive 1 full packet.
        Blocks until packet is available.
        """
        while True:
            # If we've got msgs on the queue, return one.
            if len(self._msg_q):
                return self._msg_q.pop(0)
            
            # Receive the message.
            msg = self._sock.recv(4096).decode(ENCODING)

            # Split the message into the separate packets.
            separate_packets = msg.split(SEPARATOR) 

            # Add the last partial packet to the beginning of this first one.
            separate_packets[0] = self._partial_packet + separate_packets[0]
            # We've now used the partial packet.
            self._partial_packet = ""

            # If there's a partial packet at the end of this packet
            if separate_packets[-1] != "":
                self._partial_packet = separate_packets[-1]

            # Remove the last element, because it is either "" or a partial packet.
            separate_packets.pop()

            # For each packet, convert to dict from JSON and push to queue.
            for packet in separate_packets:
                self._msg_q.append(json.loads(packet))




# print("abcabcacbacb".split("ca"))
# print("abcabcacbacb".split("a"))
# print("abcabcacbacb".split("b"))
