from unittest.mock import AsyncMock, patch

import pytest
from confy_addons.messages import (
    NOT_CONNECT_YOURSELF,
    RECIPIENT_NOT_CONNECTED,
    THE_OTHER_USER_LOGGED_OUT,
    THIS_ID_ALREADY_IN_USE,
)
from confy_addons.prefixes import SYSTEM_ERROR_PREFIX, SYSTEM_PREFIX
from fastapi import status
from fastapi.testclient import TestClient

from server.main import app
from server.routers.ws import active_connections, handle_user_disconnect, tunnel_users, waiting_for


@pytest.fixture
def client():
    return TestClient(app)


@patch('server.routers.ws.redis_client.srem', new_callable=AsyncMock)
@patch('server.routers.ws.redis_client.sadd', new_callable=AsyncMock)
@patch('server.routers.ws.redis_client.sismember', new_callable=AsyncMock)
def test_websocket_sender_recipient_same_user(mock_sismember, mock_sadd, mock_srem, client):
    """Verifica se a conexão é rejeitada quando sender_id == recipient_id."""
    mock_sismember.return_value = False

    user_id = 'user123'
    with client.websocket_connect(f'/ws/{user_id}@{user_id}') as websocket:
        data = websocket.receive_text()
        assert SYSTEM_ERROR_PREFIX in data
        assert NOT_CONNECT_YOURSELF in data


@patch('server.routers.ws.redis_client.srem', new_callable=AsyncMock)
@patch('server.routers.ws.redis_client.sadd', new_callable=AsyncMock)
@patch('server.routers.ws.redis_client.sismember', new_callable=AsyncMock)
def test_websocket_sender_already_online(mock_sismember, mock_sadd, mock_srem, client):
    """Verifica se a conexão é rejeitada quando o sender já está online."""
    mock_sismember.return_value = True

    sender_id = 'sender123'
    recipient_id = 'recipient123'
    with client.websocket_connect(f'/ws/{sender_id}@{recipient_id}') as websocket:
        data = websocket.receive_text()
        assert SYSTEM_ERROR_PREFIX in data
        assert THIS_ID_ALREADY_IN_USE in data


@patch('server.routers.ws.redis_client.srem', new_callable=AsyncMock)
@patch('server.routers.ws.redis_client.sadd', new_callable=AsyncMock)
@patch('server.routers.ws.redis_client.sismember', new_callable=AsyncMock)
def test_websocket_sender_connects_recipient_not_online(
    mock_sismember, mock_sadd, mock_srem, client
):
    """Verifica se sender recebe mensagem quando recipient não está online."""
    mock_sismember.return_value = False

    sender_id = 'sender123'
    recipient_id = 'recipient123'
    with client.websocket_connect(f'/ws/{sender_id}@{recipient_id}') as websocket:
        data = websocket.receive_text()
        assert SYSTEM_PREFIX in data
        assert RECIPIENT_NOT_CONNECTED in data


@patch('server.routers.ws.redis_client.srem', new_callable=AsyncMock)
@patch('server.routers.ws.redis_client.sadd', new_callable=AsyncMock)
@patch('server.routers.ws.redis_client.sismember', new_callable=AsyncMock)
def test_websocket_cleanup_user_from_redis(mock_sismember, mock_sadd, mock_srem, client):
    """Verifica se o usuário é removido do Redis após desconexão."""
    mock_sismember.return_value = False

    sender_id = 'sender123'
    recipient_id = 'recipient123'
    with client.websocket_connect(f'/ws/{sender_id}@{recipient_id}') as websocket:
        websocket.receive_text()

    mock_srem.assert_called()


@patch('server.routers.ws.redis_client.srem', new_callable=AsyncMock)
@patch('server.routers.ws.redis_client.sadd', new_callable=AsyncMock)
@patch('server.routers.ws.redis_client.sismember', new_callable=AsyncMock)
def test_websocket_recipient_not_connected_notification(
    mock_sismember, mock_sadd, mock_srem, client
):
    """Verifica se o sender recebe notificação quando recipient está offline."""
    mock_sismember.return_value = False

    sender_id = 'sender123'
    recipient_id = 'recipient123'
    with client.websocket_connect(f'/ws/{sender_id}@{recipient_id}') as websocket_sender:
        websocket_sender.receive_text()
        websocket_sender.send_text('Mensagem de teste')

        notification = websocket_sender.receive_text()
        assert SYSTEM_PREFIX in notification


@patch('server.routers.ws.redis_client.sismember', new_callable=AsyncMock)
def test_check_recipient_availability_offline(mock_sismember, client):
    """Verifica se o endpoint retorna que o recipient está offline."""
    mock_sismember.return_value = False
    response = client.get('/ws/check-availability/recipient123')
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data['recipient_online'] is False


@patch('server.routers.ws.redis_client.sismember', new_callable=AsyncMock)
def test_check_recipient_availability_online(mock_sismember, client):
    """Verifica se o endpoint retorna que o recipient está online."""
    mock_sismember.return_value = True
    response = client.get('/ws/check-availability/recipient123')
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data['recipient_online'] is True


@pytest.fixture
def setup_tunnel():
    """Fixture para configurar um túnel com usuários."""
    active_connections.clear()
    tunnel_users.clear()
    waiting_for.clear()

    sender_id = 'sender123'
    recipient_id = 'recipient123'
    tunnel_id = frozenset({sender_id, recipient_id})

    # Mock das WebSocket connections
    mock_sender_ws = AsyncMock()
    mock_recipient_ws = AsyncMock()

    active_connections[sender_id] = mock_sender_ws
    active_connections[recipient_id] = mock_recipient_ws
    tunnel_users[tunnel_id] = {sender_id, recipient_id}

    return sender_id, recipient_id, tunnel_id, mock_sender_ws, mock_recipient_ws


@patch('server.routers.ws.cleanup_user_from_redis')
@patch('server.routers.ws.logger')
async def test_notifies_remaining_user_on_disconnect(mock_logger, mock_cleanup, setup_tunnel):
    """Verifica se o usuário restante recebe notificação quando o outro desconecta."""
    sender_id, recipient_id, tunnel_id, mock_sender_ws, mock_recipient_ws = setup_tunnel
    mock_cleanup.return_value = None

    await handle_user_disconnect(sender_id, tunnel_id)

    # Verifica se o recipient recebeu a notificação
    expected_message = f'{SYSTEM_PREFIX} {THE_OTHER_USER_LOGGED_OUT}.'
    mock_recipient_ws.send_text.assert_called_once_with(expected_message)
    mock_recipient_ws.close.assert_called_once()


@patch('server.routers.ws.cleanup_user_from_redis')
@patch('server.routers.ws.logger')
async def test_removes_user_from_active_connections(mock_logger, mock_cleanup, setup_tunnel):
    """Verifica se o usuário é removido das conexões ativas."""
    sender_id, recipient_id, tunnel_id, mock_sender_ws, mock_recipient_ws = setup_tunnel
    mock_cleanup.return_value = None

    await handle_user_disconnect(sender_id, tunnel_id)

    # Verifica se o sender foi removido
    assert sender_id not in active_connections
    # Verifica se o recipient foi removido após notificação
    assert recipient_id not in active_connections


@patch('server.routers.ws.cleanup_user_from_redis')
@patch('server.routers.ws.logger')
async def test_cleans_up_user_from_redis(mock_logger, mock_cleanup, setup_tunnel):
    """Verifica se cleanup_user_from_redis é chamado para remover do Redis."""
    sender_id, recipient_id, tunnel_id, mock_sender_ws, mock_recipient_ws = setup_tunnel

    await handle_user_disconnect(sender_id, tunnel_id)

    # Verifica se cleanup foi chamado para o sender e recipient
    assert mock_cleanup.call_count == 2
    mock_cleanup.assert_any_call(sender_id)
    mock_cleanup.assert_any_call(recipient_id)


@patch('server.routers.ws.cleanup_user_from_redis')
@patch('server.routers.ws.logger')
async def test_handles_send_text_error(mock_logger, mock_cleanup, setup_tunnel):
    """Verifica se o código trata erros ao enviar notificação."""
    sender_id, recipient_id, tunnel_id, mock_sender_ws, mock_recipient_ws = setup_tunnel
    mock_cleanup.return_value = None

    # Simula erro ao enviar mensagem
    mock_recipient_ws.send_text.side_effect = Exception('Connection error')

    await handle_user_disconnect(sender_id, tunnel_id)

    # Verifica se o erro foi registrado
    mock_logger.error.assert_called()

    # Verifica se o usuário foi removido mesmo com erro
    assert sender_id not in active_connections
    assert recipient_id not in active_connections
    mock_cleanup.assert_called()


@patch('server.routers.ws.cleanup_user_from_redis')
@patch('server.routers.ws.logger')
async def test_handles_close_error(mock_logger, mock_cleanup, setup_tunnel):
    """Verifica se o código trata erros ao fechar a conexão."""
    sender_id, recipient_id, tunnel_id, mock_sender_ws, mock_recipient_ws = setup_tunnel
    mock_cleanup.return_value = None

    # Simula erro ao fechar conexão
    mock_recipient_ws.send_text.return_value = None
    mock_recipient_ws.close.side_effect = Exception('Close error')

    await handle_user_disconnect(sender_id, tunnel_id)

    # Verifica se o usuário foi removido mesmo com erro no close
    assert recipient_id not in active_connections
    mock_cleanup.assert_called()


@patch('server.routers.ws.cleanup_user_from_redis')
@patch('server.routers.ws.logger')
async def test_removes_tunnel_when_empty(mock_logger, mock_cleanup, setup_tunnel):
    """Verifica se o túnel é removido quando fica vazio."""
    sender_id, recipient_id, tunnel_id, mock_sender_ws, mock_recipient_ws = setup_tunnel
    mock_cleanup.return_value = None

    await handle_user_disconnect(sender_id, tunnel_id)

    # Verifica se o túnel foi removido
    assert tunnel_id not in tunnel_users


@patch('server.routers.ws.cleanup_user_from_redis')
@patch('server.routers.ws.logger')
async def test_user_not_in_active_connections(mock_logger, mock_cleanup, setup_tunnel):
    """Verifica se o código trata quando o usuário não está em active_connections."""
    sender_id, recipient_id, tunnel_id, mock_sender_ws, mock_recipient_ws = setup_tunnel
    mock_cleanup.return_value = None

    # Remove o recipient das conexões ativas antes do desconect
    del active_connections[recipient_id]

    await handle_user_disconnect(sender_id, tunnel_id)

    # Verifica se sender foi removido
    assert sender_id not in active_connections
    # Verifica se cleanup foi chamado
    mock_cleanup.assert_called()


@patch('server.routers.ws.cleanup_user_from_redis')
@patch('server.routers.ws.logger')
async def test_clears_waiting_for_list(mock_logger, mock_cleanup, setup_tunnel):
    """Verifica se a lista de espera é limpa ao desconectar."""
    sender_id, recipient_id, tunnel_id, _, _ = setup_tunnel
    mock_cleanup.return_value = None

    # Adiciona o sender à lista de espera
    waiting_for[sender_id] = ['other_user1', 'other_user2']

    await handle_user_disconnect(sender_id, tunnel_id)

    # Verifica se a lista de espera foi limpa
    assert sender_id not in waiting_for


@patch('server.routers.ws.cleanup_user_from_redis')
@patch('server.routers.ws.logger')
async def test_removes_from_all_waiting_lists(mock_logger, mock_cleanup, setup_tunnel):
    """Verifica se o usuário é removido de todas as listas de espera."""
    sender_id, recipient_id, tunnel_id, mock_sender_ws, mock_recipient_ws = setup_tunnel
    mock_cleanup.return_value = None

    # Adiciona o sender em múltiplas listas de espera
    waiting_for['user1'] = [sender_id, 'other_user']
    waiting_for['user2'] = [sender_id]

    await handle_user_disconnect(sender_id, tunnel_id)

    # Verifica se foi removido de todas as listas
    assert sender_id not in waiting_for['user1']
    assert sender_id not in waiting_for['user2']
