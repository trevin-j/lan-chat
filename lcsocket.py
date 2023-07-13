from typing import Dict
import socket
import json
from crypto import encrypt, decrypt


class LCSocket:
    def __init__(self, sock: socket.socket) -> None:
        self._msg_q = []
        self._partial_packet = ""
        self._sock: socket.socket = sock

        # Socket should already be connected at construction of LCSocket
        self._connected = True

        self._encryption_key = None

    def set_encryption_key(self, key):
        """ Set the encryption key and enable encryption from here on. """
        self._encryption_key = key

    def full_send(self, data: Dict[str, str]) -> None:
        """
        Send a full packet.
        """
        if self._encryption_key is None:
            self._sock.sendall(json.dumps(data).encode())
            return
        
        self._sock.sendall(encrypt(self._encryption_key, json.dumps(data)))

    def full_receive(self) -> Dict[str, str]:
        """
        Receive 1 full packet.
        Blocks until packet is available.
        """
        if self._encryption_key is None:
            msg = self._sock.recv(4096).decode()
            return json.loads(msg)
        
        msg = decrypt(self._encryption_key, self._sock.recv(4096))
        return json.loads(msg)
           

    def settimeout(self, timeout: float) -> None:
        self._sock.settimeout(timeout)
        
    def close(self) -> None:
        self._connected = False
        return self._sock.close()
    
    def is_connected(self) -> bool:
        return self._connected

