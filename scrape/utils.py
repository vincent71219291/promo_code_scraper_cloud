import hashlib


def generate_hash_key_md5(string: str) -> str:
    return hashlib.md5(string.encode()).hexdigest()
