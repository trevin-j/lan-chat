"""
Functions for getting prime numbers.
"""

from random import randrange

def get_random_bit_sized_int(size: int) -> int:
    """
    Get a random number of `size` number of bits.
    """
    return randrange(2**(size-1) + 1, 2**size - 1)

def is_low_lvl_prime(num: int) -> bool:
    """
    Check if the number is a prime by checking if any small primes divide into it.
    """
    first_primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59,
                    61, 67, 71, 73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127, 131,
                    137, 139, 149, 151, 157, 163, 167, 173, 179, 181, 191, 193, 197,
                    199, 211, 223, 227, 229, 233, 239, 241, 251, 257, 263, 269, 271,
                    277, 281, 283, 293, 307, 311, 313, 317, 331, 337, 347, 349]

    for divisor in first_primes:
        if num % divisor == 0:
            break

        return True

    return False

# I didn't feel like implementing Rabin Miller test myself.
# https://www.geeksforgeeks.org/how-to-generate-large-prime-numbers-for-rsa-algorithm/
# Modified to fit actual Python conventions. MEANING NO CAMELCASE
# THIS IS PYTHON NOT JAVA
# -------------------------------------------------------------------------------------------------
def is_high_lvl_prime(num: int) -> bool:
    """
    Use Rabin Miller algorithm to check if prime.
    """
    max_division_by_two = 0
    even_component = num-1

    while even_component % 2 == 0:
        even_component >>= 1
        max_division_by_two += 1
    assert 2**max_division_by_two * even_component == num-1

    def trial_composite(round_tester):
        if pow(round_tester, even_component, num) == 1:
            return False
        for i in range(max_division_by_two):
            if pow(round_tester, 2**i * even_component, num) == num - 1:
                return False
        return True

    # Set number of trials here
    number_of_rabin_trials = 2**10
    for _ in range(number_of_rabin_trials):
        round_tester = randrange(2, num)
        if trial_composite(round_tester):
            return False
    return True
# ------------------------------------------------------------------------------------


def get_prime_of_size(size: int) -> int:
    """
    Get a prime number with `size` number of bits.
    """
    while True:
        # print("Getting random pc")
        prime_candidate = get_random_bit_sized_int(size)
        # print("Checking if pc is low lvl prime")
        if not is_low_lvl_prime(prime_candidate):
            continue
        # print("Checking if pc is high lvl prime")
        if is_high_lvl_prime(prime_candidate):
            print()
            return prime_candidate
