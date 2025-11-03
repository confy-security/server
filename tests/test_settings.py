from server import settings


def setup_function(function):
    # Ensure clear cache before each test
    settings.get_settings.cache_clear()


def teardown_function(function):
    # Clear cache and remove possible environment variables between tests
    settings.get_settings.cache_clear()


def test_defaults(monkeypatch):
    monkeypatch.delenv('REDIS_HOST', raising=False)
    monkeypatch.delenv('REDIS_PORT', raising=False)

    s = settings.get_settings()
    assert s.REDIS_HOST == 'localhost'
    assert s.REDIS_PORT == 6379


def test_env_override(monkeypatch):
    monkeypatch.setenv('REDIS_HOST', 'redis.example')
    monkeypatch.setenv('REDIS_PORT', '6380')

    s = settings.get_settings()
    assert s.REDIS_HOST == 'redis.example'
    assert s.REDIS_PORT == 6380


def test_memoization(monkeypatch):
    monkeypatch.delenv('REDIS_HOST', raising=False)
    monkeypatch.delenv('REDIS_PORT', raising=False)

    s1 = settings.get_settings()
    s2 = settings.get_settings()
    assert s1 is s2  # same instance by lru_cache

    # changing env without clearing cache does not change the already cached instance
    monkeypatch.setenv('REDIS_HOST', 'changed-host')
    s3 = settings.get_settings()
    assert s3 is s1
    assert s3.REDIS_HOST == 'localhost'

    # after clearing cache, new instance reflects environment variables
    settings.get_settings.cache_clear()
    s4 = settings.get_settings()
    assert s4 is not s1
    assert s4.REDIS_HOST == 'changed-host'
