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



def add_chat(msg):
    chat_history.insert(0, msg)
    print_chat()


def print_nol(string: str, flush=True):
    print(string, end="", flush=flush)

def clear_current_line():
    sys.stdout.write("\033[2K\033[1G")

def clear_last_line():
    sys.stdout.write("\033[F\033[2K\033[1G")


for i in range(20):
    print()

def process_word_wrap(msgs):
    terminal_width = get_terminal_size()[0]
    new_msgs = []
    for msg in msgs:
        while True:
            if len(msg) > terminal_width:
                new_msgs.append(msg[:terminal_width]+"\n")
                msg = msg[terminal_width:]
            else:
                new_msgs.append(msg)
                break
            
    return new_msgs


def t_print_msgs(client: LCSocket):
    while True:
        data = client.full_receive()
        msg = data["message"]
        sender = data["source"]

        msgs = [sender + ": " + msg]

        msgs = process_word_wrap(msgs)

        for m in msgs:
            add_chat(m)




