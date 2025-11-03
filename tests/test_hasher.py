from server.hasher import hash_id


def test_hash_id_returns_string():
    result = hash_id('user123')
    assert isinstance(result, str)


def test_hash_id_returns_valid_hex():
    result = hash_id('user123')
    assert len(result) == 64  # SHA256 hexdigest tem 64 caracteres
    assert all(c in '0123456789abcdef' for c in result)


def test_hash_id_consistency():
    user_id = 'john@example.com'
    hash1 = hash_id(user_id)
    hash2 = hash_id(user_id)
    assert hash1 == hash2


def test_hash_id_different_inputs_different_outputs():
    hash1 = hash_id('user1')
    hash2 = hash_id('user2')
    assert hash1 != hash2


def test_hash_id_empty_string():
    result = hash_id('')
    assert isinstance(result, str)
    assert len(result) == 64


def test_hash_id_unicode_characters():
    result = hash_id('usuário@café.com')
    assert isinstance(result, str)
    assert len(result) == 64


def test_hash_id_long_string():
    long_id = 'a' * 1000
    result = hash_id(long_id)
    assert len(result) == 64
