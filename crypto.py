"""
Functions for encryption and decryption.
"""

from typing import Tuple
import random

import pyDes

from prime import get_prime_of_size

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

def diffie_first_step(secret_key: int, large_prime_n: int, prime_g: int) -> int:
    """
    Returns the portion of the key to send to the other client. 
    args:
        secret_key: Your unshared secret key.
        n: Large prime number, must be same as other client. It can be known.
        g: Generator. Should be prime root of n.
    """
    return pow(prime_g, secret_key, large_prime_n)

def diffie_second_step(public_key: int, secret_key: int, large_prime_n: int) -> int:
    """
    Returns the final symmetrical secret key.
    args:
        public_key: The other client's public key.
        secret_key: Your unshared secret key.
        n: Large prime number, must be same as other client. It can be known.
    """
    return pow(public_key, secret_key, large_prime_n)

def get_private_key(large_prime_n: int) -> int:
    """
    Get a private key.
    """
    return random.randint(1,large_prime_n)
