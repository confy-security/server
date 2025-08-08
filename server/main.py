"""
Confy Server - Endpoint WebSocket para comunicação em tempo real entre usuários.

Este módulo define um endpoint WebSocket para uma aplicação FastAPI que permite a comunicação em tempo real entre usuários.
Ele gerencia conexões ativas, túneis de comunicação e usuários que estão aguardando por destinatários específicos.
As mensagens são encaminhadas entre usuários conectados, e o sistema notifica os remetentes quando
os destinatários se conectam ou desconectam.
O endpoint é acessível via URL no formato `/ws/{sender_id}@{recipient_id}`,
onde `sender_id` é o ID do remetente e `recipient_id` é o ID do destinatário.
As conexões são gerenciadas por meio de um dicionário de conexões ativas e um conjunto de túneis ativos.
Quando um usuário se conecta, o sistema verifica se o destinatário está online.
Se não estiver, o remetente é adicionado a uma lista de espera.
Quando o destinatário se conecta, todos os remetentes que estavam aguardando são notificados.
As mensagens são enviadas como texto simples, e o sistema lida com desconexões de usuários,
removendo conexões e notificando os destinatários conforme necessário.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from server.logger import logger

description = """
Este servidor realiza o encaminhamento de mensagens entre usuários conectados
via WebSocket utilizando algum aplicativo cliente compatível com o servidor.
"""

app = FastAPI(
    title='Confy Server',
    description=description,
    version='0.0.1.dev1',
    terms_of_service='https://github.com/confy-security/server/blob/main/LICENSE',
    contact={
        'name': 'Confy Security Team',
        'url': 'https://github.com/confy-security/server',
        'email': 'confy@henriquesebastiao.com',
    },
)

# Dicionário para armazenar conexões WebSocket ativas no formato {user_id: websocket}
active_connections: dict[str, WebSocket] = {}

# Conjunto de túneis ativos representando pares de usuários que estão se comunicando
active_tunnels = set()

# Dicionário para armazenar usuários que estão esperando pelo destinatário
waiting_for: dict[str, list[str]] = {}


@app.websocket('/ws/{sender_id}@{recipient_id}')
async def websocket_endpoint(websocket: WebSocket, sender_id: str, recipient_id: str):
    """
    Estabelece uma conexão WebSocket entre dois usuários.

    Args:
        websocket (WebSocket): A conexão WebSocket do remetente.
        sender_id (str): O ID do remetente.
        recipient_id (str): O ID do destinatário.

    """
    # Aceita a conexão WebSocket do cliente
    await websocket.accept()

    # Registra a conexão do remetente como ativa
    active_connections[sender_id] = websocket

    # Cria um identificador único e imutável para o túnel de comunicação
    tunnel_id = frozenset({sender_id, recipient_id})

    active_tunnels.add(tunnel_id)

    logger.info(f'Usuário {sender_id} conectado.')

    # Se o destinatário ainda não estiver conectado, avisa o remetente
    if recipient_id not in active_connections:
        # Adiciona o remetente à lista de espera pelo destinatário
        waiting_for.setdefault(recipient_id, []).append(sender_id)

        await websocket.send_text(
            'system-message: O destinatário ainda não está conectado. '
            'Você será notificado quando ele estiver online.'
        )

    # Verifica se alguém estava aguardando por este usuário
    if sender_id in waiting_for:
        for waiting_sender in waiting_for[sender_id]:
            if waiting_sender in active_connections:
                await active_connections[waiting_sender].send_text(
                    'system-message: O usuário destinatário agora está conectado.'
                )
        del waiting_for[sender_id]

    try:
        while True:
            # Aguarda o recebimento de uma mensagem do remetente
            message = await websocket.receive_text()

            # Se o destinatário estiver conectado, encaminha a mensagem
            if recipient_id in active_connections:
                await active_connections[recipient_id].send_text(message)
            else:
                # Se o destinatário não estiver conectado, avisa o remetente
                await websocket.send_text(
                    'system-message: O outro usuário ainda não está conectado.'
                )

    # Se o remetente desconectar, remove a conexão e notifica o destinatário
    except WebSocketDisconnect:
        # Remoção da conexão do remetente do dicionário de conexões ativas
        if sender_id in active_connections:
            del active_connections[sender_id]

        # Se o destinatário ainda estiver conectado, avisa e encerra a conexão dele também
        if recipient_id in active_connections:
            recipient_connection = active_connections[recipient_id]
            await recipient_connection.send_text('system-message: O outro usuário se desconectou.')
            await recipient_connection.close()
            del active_connections[recipient_id]

        # Remove o túnel lógico entre os usuários
        if tunnel_id in active_tunnels:
            active_tunnels.remove(tunnel_id)

        logger.info(f'Usuário {sender_id} desconectado.')
