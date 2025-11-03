from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from server import main as m
from server.routers import online_users, status, ws


def test_app_metadata():
    assert m.app.title == 'Confy Server'
    assert m.app.version.startswith('0.0.1')
    assert m.app.contact['email'] == 'confy@henriquesebastiao.com'


def _paths_of(router):
    return {r.path for r in router.routes}


def test_routers_registered():
    app_paths = {r.path for r in m.app.routes}
    for router in (ws.router, status.router, online_users.router):
        for p in _paths_of(router):
            assert p in app_paths


@pytest.mark.asyncio
async def test_lifespan_cleans_online_users():
    mock_delete = AsyncMock()

    with patch(
        'server.main.redis_client',
        new_callable=lambda: type('obj', (), {'delete': mock_delete})(),
        create=True,
    ):
        async with m.clean_online_users(m.app):
            pass

        mock_delete.assert_called_once_with('online_users')


def test_lifespan_integration():
    mock_delete = AsyncMock()

    with patch('server.main.redis_client.delete', mock_delete):
        with TestClient(m.app):
            pass

        mock_delete.assert_called_once_with('online_users')
