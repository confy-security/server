import hashlib


def hash_id(user_id: str) -> str:
    """
    Generates the hash of a given string.

    Args:
        user_id (str): Text to hash

    Returns:
        str: Hash of the provided text

    """
    return hashlib.sha256(user_id.encode('utf-8')).hexdigest()