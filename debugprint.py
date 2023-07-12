DEBUG_SERVER = False
DEBUG_CLIENT = False

def sprint(*args, **kwargs):
    if DEBUG_SERVER:
        print("SERVER:", *args, **kwargs)

def cprint(*args, **kwargs):
    if DEBUG_CLIENT:
        print("CLIENT:", *args, **kwargs)
