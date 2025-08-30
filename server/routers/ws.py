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

# Dicionário para rastrear quais usuários fazem parte de cada túnel
tunnel_users: dict[frozenset, set[str]] = {}


async def cleanup_user_from_redis(user_id: str):
    """
    Remove um usuário do Redis e limpa suas referências.

    Args:
        user_id (str): ID do usuário para remover

    """
    await redis_client.srem('online_users', user_id)
    logger.info(f'Usuário {user_id} removido do Redis.')


async def handle_user_disconnect(disconnected_user: str, tunnel_id: frozenset):
    """
    Gerencia a desconexão de um usuário, incluindo limpeza de conexões e notificações.

    Args:
        disconnected_user (str): ID do usuário que se desconectou
        tunnel_id (frozenset): ID do túnel que o usuário fazia parte

    """
    # Remove o usuário desconectado do dicionário de conexões ativas
    if disconnected_user in active_connections:
        del active_connections[disconnected_user]

    # Remove o usuário do Redis
    await cleanup_user_from_redis(disconnected_user)

    # Remove o usuário da lista de usuários do túnel
    if tunnel_id in tunnel_users:
        tunnel_users[tunnel_id].discard(disconnected_user)

        # Se ainda há usuários conectados neste túnel, notifica-os
        remaining_users = tunnel_users[tunnel_id].copy()
        for user_id in remaining_users:
            if user_id in active_connections:
                try:
                    await active_connections[user_id].send_text(
                        'system-message: O outro usuário se desconectou.'
                    )
                    await active_connections[user_id].close()

                    # Remove o usuário restante das conexões ativas
                    del active_connections[user_id]
                    # Remove o usuário restante do Redis
                    await cleanup_user_from_redis(user_id)

                except Exception as e:
                    logger.error(f'Erro ao notificar usuário {user_id}: {e}')
                    # Remove mesmo se houver erro na notificação
                    if user_id in active_connections:
                        del active_connections[user_id]
                    await cleanup_user_from_redis(user_id)

        # Remove o túnel quando todos os usuários se desconectaram
        del tunnel_users[tunnel_id]
        if tunnel_id in active_tunnels:
            active_tunnels.remove(tunnel_id)

    # Limpa a lista de espera se o usuário desconectado estava sendo aguardado
    if disconnected_user in waiting_for:
        del waiting_for[disconnected_user]

    # Remove o usuário de todas as listas de espera onde ele possa estar
    for recipient, senders in waiting_for.items():
        if disconnected_user in senders:
            senders.remove(disconnected_user)


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

    # Registra os usuários que fazem parte deste túnel
    if tunnel_id not in tunnel_users:
        tunnel_users[tunnel_id] = set()
    tunnel_users[tunnel_id].add(sender_id)

    # Se o destinatário também estiver conectado, adiciona-o ao túnel
    if recipient_id in active_connections:
        tunnel_users[tunnel_id].add(recipient_id)

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
                # Adiciona o sender que estava esperando ao túnel
                tunnel_users[tunnel_id].add(waiting_sender)
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

    # Se o remetente desconectar, gerencia a limpeza adequadamente
    except WebSocketDisconnect:
        logger.info(f'Usuário {sender_id} desconectado.')
        await handle_user_disconnect(sender_id, tunnel_id)
