from unittest.mock import AsyncMock, patch

import pytest
from confy_addons.http_messages import DETAIL_USERNAME_NOT_AVAILABLE, MESSAGE_USERNAME_AVAILABLE
from fastapi import status
from fastapi.testclient import TestClient

from server.hasher import hash_id
from server.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.asyncio
async def test_check_username_availability_available():
    mock_sismember = AsyncMock(return_value=False)

    with patch('server.routers.online_users.redis_client.sismember', mock_sismember):
        client = TestClient(app)
        response = client.get('/online-users/john_doe')

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {'message': MESSAGE_USERNAME_AVAILABLE}
        mock_sismember.assert_called_once_with('online_users', hash_id('john_doe'))


@pytest.mark.asyncio
async def test_check_username_availability_not_available():
    mock_sismember = AsyncMock(return_value=True)

    with patch('server.routers.online_users.redis_client.sismember', mock_sismember):
        client = TestClient(app)
        response = client.get('/online-users/john_doe')

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json() == {'detail': DETAIL_USERNAME_NOT_AVAILABLE}
        mock_sismember.assert_called_once_with('online_users', hash_id('john_doe'))


@pytest.mark.asyncio
async def test_check_username_availability_hashes_user_id():
    mock_sismember = AsyncMock(return_value=False)

    with patch('server.routers.online_users.redis_client.sismember', mock_sismember):
        client = TestClient(app)
        user_id = 'user@example.com'
        response = client.get(f'/online-users/{user_id}')

        assert response.status_code == status.HTTP_200_OK
        mock_sismember.assert_called_once_with('online_users', hash_id(user_id))
        assert mock_sismember.call_args[0][1] == hash_id(user_id)


@pytest.mark.asyncio
async def test_check_username_availability_special_characters():
    mock_sismember = AsyncMock(return_value=False)

    with patch('server.routers.online_users.redis_client.sismember', mock_sismember):
        client = TestClient(app)
        response = client.get('/online-users/user_with-special.chars123')

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {'message': MESSAGE_USERNAME_AVAILABLE}
