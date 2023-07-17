import sys
from os import get_terminal_size
from lcsocket import LCSocket

chat_history = ["\033[2K"]


def print_chat():
    # Save cursor position
    print_nol("\033[s", flush=False)

    for i in range(len(chat_history)):
        # Move cursor up one line and clear it
        print_nol("\033[F\033[2K\033[1G", flush=False)
        print_nol(chat_history[i], flush=False)
        # print_nol("\033[F") # <- get rid of \n from chat history

    print_nol((len(chat_history)) * "\033[E")

    # Return to saved position
    print_nol("\033[u")



def add_chat(msg: str):
    for line in msg.split("\n"):
        chat_history.insert(0, line)
    print_chat()


def print_nol(string: str, flush=True):
    print(string, end="", flush=flush)

def clear_current_line():
    sys.stdout.write("\033[2K\033[1G")

def clear_last_line():
    sys.stdout.write("\033[F\033[2K\033[1G")

def process_word_wrap(msg):
    terminal_width = get_terminal_size()[0]
    new_msgs = []
    while True:
        if len(msg) > terminal_width:
            new_msgs.append(msg[:terminal_width]+"\n")
            msg = msg[terminal_width:]
        else:
            new_msgs.append(msg)
            break
            
    return new_msgs


# Thread
def msg_handler(client: LCSocket):
    for i in range(get_terminal_size()[1]):
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
