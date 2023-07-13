from random import randrange

def get_random_bit_sized_int(size: int) -> int:
    return randrange(2**(size-1) + 1, 2**size - 1)

def is_low_lvl_prime(num: int) -> bool:
    first_primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127, 131, 137, 139, 149, 151, 157, 163, 167, 173, 179, 181, 191, 193, 197, 199, 211, 223, 227, 229, 233, 239, 241, 251, 257, 263, 269, 271, 277, 281, 283, 293, 307, 311, 313, 317, 331, 337, 347, 349]
    
    for divisor in first_primes:
        if num % divisor == 0:
            break

        return True

    return False

# I didn't feel like implementing Rabin Miller test myself.
# 
# https://www.geeksforgeeks.org/how-to-generate-large-prime-numbers-for-rsa-algorithm/
# -------------------------------------------------------------------------------------------------
def is_high_lvl_prime(num: int) -> bool:
    global prime_candidates_rejected
    maxDivisionsByTwo = 0
    evenComponent = num-1
   
    while evenComponent % 2 == 0:
        evenComponent >>= 1
        maxDivisionsByTwo += 1
    assert(2**maxDivisionsByTwo * evenComponent == num-1)
   
    def trialComposite(round_tester):
        if pow(round_tester, evenComponent, 
               num) == 1:
            return False
        for i in range(maxDivisionsByTwo):
            if pow(round_tester, 2**i * evenComponent,
                   num) == num - 1:
                return False
        return True
   
    # Set number of trials here
    numberOfRabinTrials = 2**10
    for i in range(numberOfRabinTrials):
        round_tester = randrange(2, num)
        if trialComposite(round_tester):
            return False
    return True
# ------------------------------------------------------------------------------------


def get_prime_of_size(size: int) -> int:
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



