import random

from config import DIGIT_COUNT


def generate_secret() -> str:
    """Генерує секретне число з DIGIT_COUNT унікальних цифр."""
    digits = random.sample("0123456789", DIGIT_COUNT)
    if digits[0] == "0":
        digits[0], digits[1] = digits[1], digits[0]
    return "".join(digits)


def count_bulls_and_cows(secret: str, guess: str) -> tuple[int, int]:
    """Підраховує биків та корів."""
    bulls = sum(s == g for s, g in zip(secret, guess))
    cows = sum(g in secret for g in guess) - bulls
    return bulls, cows