from fastapi.testclient import TestClient

from server.main import app


def test_connection_on_server():
    client = TestClient(app)
    with client.websocket_connect('/ws/pedro@maria') as websocket:
        data = websocket.receive_text()
        assert data == (
            'system-message: O destinatário ainda não está conectado. '
            'Você será notificado quando ele estiver online.'
        )


def test_notification_when_recipient_connects():
    client_pedro = TestClient(app)
    with client_pedro.websocket_connect('/ws/pedro@maria') as websocket_pedro:
        data = websocket_pedro.receive_text()
        assert data == (
            'system-message: O destinatário ainda não está conectado. '
            'Você será notificado quando ele estiver online.'
        )

        client_maria = TestClient(app)
        with client_maria.websocket_connect('/ws/maria@pedro'):
            data_with_notification = websocket_pedro.receive_text()

            assert data_with_notification == (
                'system-message: O usuário destinatário agora está conectado.'
            )


def test_notification_that_recipient_is_still_offline_if_sender_sends_something():
    client = TestClient(app)
    with client.websocket_connect('/ws/pedro@maria') as websocket:
        data = websocket.receive_text()
        assert data == (
            'system-message: O destinatário ainda não está conectado. '
            'Você será notificado quando ele estiver online.'
        )
        websocket.send_text('Enviando mensagem.')
        data = websocket.receive_text()
        assert data == 'system-message: O outro usuário ainda não está conectado.'


def test_notification_if_recipient_disconnects():
    client_pedro = TestClient(app)
    with client_pedro.websocket_connect('/ws/pedro@maria') as websocket_pedro:
        data = websocket_pedro.receive_text()
        assert data == (
            'system-message: O destinatário ainda não está conectado. '
            'Você será notificado quando ele estiver online.'
        )

        client_maria = TestClient(app)
        with client_maria.websocket_connect('/ws/maria@pedro') as websocket_maria:
            data = websocket_pedro.receive_text()

            assert data == 'system-message: O usuário destinatário agora está conectado.'

            websocket_pedro.close()
            data = websocket_maria.receive_text()

            assert data == 'system-message: O outro usuário se desconectou.'
