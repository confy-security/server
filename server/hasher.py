import hashlib


def hash_id(user_id: str) -> str:
    """
    Gera o hash de uma determinada string.

    Args:
        user_id (str): Texto para obter o hash

    Returns:
        str: Hash do texto informado

    """
    return hashlib.sha256(user_id.encode('utf-8')).hexdigest()
