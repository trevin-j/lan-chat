"""
Functions to display a clean client UI.
"""

import sys
from os import get_terminal_size

from lcsocket import LCSocket


chat_history = ["\033[2K"]

def print_chat():
    """
    Print out the messages in a nice manner.
    """
    # Save cursor position
    print_nol("\033[s", flush=False)

    for chat in chat_history:
        # Move cursor up one line and clear it
        print_nol("\033[F\033[2K\033[1G", flush=False)
        print_nol(chat, flush=False)

    print_nol((len(chat_history)) * "\033[E")

    # Return to saved position
    print_nol("\033[u")



def add_chat(msg: str):
    """
    Add a chat to the chat history and display chats.
    """
    for line in msg.split("\n"):
        chat_history.insert(0, line)
    print_chat()


def print_nol(string: str, flush=True):
    """
    Print with no line.
    """
    print(string, end="", flush=flush)


def clear_current_line():
    """
    Clear the current line.
    """
    sys.stdout.write("\033[2K\033[1G")


def clear_last_line():
    """
    Clear the last line.
    """
    sys.stdout.write("\033[F\033[2K\033[1G")


def msg_handler(client: LCSocket):
    """
    A thread function to receive messages and display them.
    """
    for _ in range(get_terminal_size()[1]):
        print()

    while True:
        # When trying to receive from client, will raise AttributeError if host disconnected.
        try:
            data = client.full_receive()
        except AttributeError:
            client.close()
            add_chat("Host unexpectedly disconnected. Press enter to exit.")
            return

        msg = data["message"]
        sender = data["source"]

        msg = "[" + sender + "] " + msg

        add_chat(msg)

        if data["action"] == "DISCONNECT":
            client.close()
            return
