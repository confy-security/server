"""
Endpoint WebSocket para comunicação em tempo real entre usuários.

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

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from server.db import redis_client
from server.hasher import hash_id
from server.logger import logger

router = APIRouter(prefix='/ws', tags=['WebSocket'])

# Dicionário para armazenar conexões WebSocket ativas no formato {user_id: websocket}
active_connections: dict[str, WebSocket] = {}

# Conjunto de túneis ativos representando pares de usuários que estão se comunicando
active_tunnels = set()

# Dicionário para armazenar usuários que estão esperando pelo destinatário
waiting_for: dict[str, list[str]] = {}


@router.websocket('/{sender_id}@{recipient_id}')
async def websocket_endpoint(websocket: WebSocket, sender_id: str, recipient_id: str):
    """
    Estabelece uma conexão WebSocket entre dois usuários.

    Args:
        websocket (WebSocket): A conexão WebSocket do remetente.
        sender_id (str): O ID do remetente.
        recipient_id (str): O ID do destinatário.

    """
    sender_id = hash_id(sender_id)
    recipient_id = hash_id(recipient_id)

    # Aceita a conexão WebSocket do cliente
    await websocket.accept()

    # Verifica no Redis se o usuário já está conectado
    is_online = await redis_client.sismember('online_users', sender_id)
    if is_online:
        await websocket.send_text(
            'system-message: Já há um usuário conectado com o ID que você solicitou.'
        )
        await websocket.close()
        return  # encerra a função sem registrar o usuário novamente

    # Registra a conexão do remetente como ativa
    active_connections[sender_id] = websocket

    # Salva no Redis que o usuário está online
    await redis_client.sadd('online_users', sender_id)

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

            # Remove do Redis quando desconectar
            await redis_client.srem('online_users', sender_id)

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
