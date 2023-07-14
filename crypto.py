import pyDes
from prime import get_prime_of_size
from typing import Tuple
import random

def encrypt(key: int, value: str) -> bytes:
    """ Encrypt value using DES and the symmetric key. """
    encrypter = pyDes.des(key.to_bytes(8, "big"), pad=None, padmode=pyDes.PAD_PKCS5)
    return encrypter.encrypt(value.encode())

def decrypt(key: int, encrypted_value_bytes: bytes) -> str:
    """ Decrypt value using DES and the symmetric key. """
    decrypter = pyDes.des(key.to_bytes(8, "big"), pad=None, padmode=pyDes.PAD_PKCS5)
    return decrypter.decrypt(encrypted_value_bytes).decode()

def get_n_and_g() -> Tuple[int, int]:
    """ Get a suitable n and g value such that we can use DES. Returns (n, g). """
    return get_prime_of_size(64), get_prime_of_size(32)

def diffie_first_step(secret_key: int, n: int, g: int) -> int:
    """
    Returns the portion of the key to send to the other client. 
    args:
        secret_key: Your unshared secret key.
        n: Large prime number, must be same as other client. It can be known.
        g: Generator. Should be prime root of n. IDK what that means so I use 13 cause it's a relatively small prime.
    """
    return pow(g, secret_key, n)

def diffie_second_step(partial_key: int, secret_key: int, n: int) -> int:
    """
    Returns the final symmetrical secret key.
    args:
        partial_key: The partial key sent by the other client.
        secret_key: Your unshared secret key.
        n: Large prime number, must be same as other client. It can be known.
    """
    return pow(partial_key, secret_key, n)

def get_private_key(n: int) -> int:
    return random.randint(1,n)
