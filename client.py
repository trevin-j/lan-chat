import socket
import sys
from server import Server, DEFAULT_PORT, BROADCAST_RESPONSE, BROADCAST_PACKET
from lcsocket import LCSocket
from debugprint import cprint
from client_ui import msg_handler, clear_current_line
import threading
import netifaces
from typing import Tuple, List
import time


def user_choose_host() -> str:
    # get available rooms
    hosts = get_available_rooms()
    # user choice for which one
    print(f"Found {len(hosts)} hosts.")
    for i, host in enumerate(hosts):
        print(f"{i}: {host[0]} -- {host[1]}")
    # return hostname of user choice
    try:
        choice = int(input("Choose host> "))
        return hosts[choice][1]
    except:
        # Don't bother with user being dumb or if no hosts.
        return None


def connect_to_server() -> socket.socket:
    """ Connect to the server with the argv hostname and port. False indicates failed in some way. """
    hostname = ""
    
    try:
        direct_loc = sys.argv.index("--direct")
        hostname = sys.argv[direct_loc+1]
    except ValueError:
        pass
    except IndexError:
        print("Specify the hostname after --direct")
        return False
    
    if "--host" in sys.argv: hostname = "localhost"
    elif hostname == "": hostname = user_choose_host()
    if hostname is None: return False

    port = DEFAULT_PORT
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((hostname, port))

    return sock
    

def get_broadcast_addresses() -> str:
    broadcast_addresses = []

    for interface in netifaces.interfaces():
        addresses = netifaces.ifaddresses(interface)
        for addr_group in addresses[netifaces.AF_INET]:
            try:
                broadcast_addresses.append(addr_group["broadcast"])
            except:
                continue

    return broadcast_addresses


def get_available_rooms() -> List[Tuple[str, str]]:
    broadcast_addresses = get_broadcast_addresses()

    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.settimeout(0.25)
    
    # Tell socket to allow broadcasting.
    udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    for broadcast_address in broadcast_addresses:
        udp_sock.sendto(BROADCAST_PACKET.encode(), (broadcast_address, DEFAULT_PORT))
    
    all_rooms = []

    try:
        while True:
            response, addr = udp_sock.recvfrom(4096)
            response = response.decode()
            if BROADCAST_RESPONSE in response:
                name = response.split(BROADCAST_RESPONSE)[1]
                all_rooms.append((name,addr[0]))
    except TimeoutError:
        pass

    return all_rooms


def main():
    if "--find" in sys.argv:
        rooms = get_available_rooms()
        print(f"Found {len(rooms)} hosts.")
        for room in rooms:
            print(f"{room[0]} -- {room[1]}")
        return
    
    name = False

    am_host = "--host" in sys.argv
    if am_host:
        room_name = input("Room name: ")
        name = input("Name: ")
        print("Hosting.")
        server = Server(room_name)
        server.start()
        if not "--invisible" in sys.argv:
            server.make_visible()
    else:
        pass

    raw_connection = connect_to_server()
    if not raw_connection:
        return
    lcsocket = LCSocket(raw_connection)    
    if not name:
        name = input("Name: ")
    lcsocket.full_send({"action": "CONNECT", "message": name, "source": name})

    ui_thread = threading.Thread(target=msg_handler, args=(lcsocket,))
    ui_thread.start()
    time.sleep(0.1)

    while True:
        msg = input("> ")
        clear_current_line()
        if not lcsocket.is_connected():
            break
        if msg != "":
            lcsocket.full_send({"action": "MESSAGE", "message": msg, "source": name})

    if am_host:
        server.join()

    ui_thread.join()
        




if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Exiting.")
        sys.exit()
    