"""
WebSocket endpoint for real-time communication between users.

This module defines a WebSocket endpoint for a FastAPI application that enables real-time
communication between users. It manages active connections, communication tunnels, and users
waiting for specific recipients. Messages are forwarded between connected users, and the system
notifies senders when recipients connect or disconnect.
The endpoint is accessible via URL in the format `/ws/{sender_id}@{recipient_id}`,
where `sender_id` is the sender's ID and `recipient_id` is the recipient's ID.
Connections are managed through a dictionary of active connections and a set of active tunnels.
When a user connects, the system checks if the recipient is online.
If not, the sender is added to a waiting list.
When the recipient connects, all senders who were waiting are notified.
Messages are sent as plain text, and the system handles user disconnections,
removing connections and notifying recipients as necessary.
"""

from confy_addons.http_messages import (
    DETAIL_RECIPIENT_IS_ALREADY_CHATTING,
    MESSAGE_AVAILABLE_RECIPIENT,
)
from confy_addons.messages import (
    NOT_CONNECT_YOURSELF,
    RECIPIENT_CONNECTED,
    RECIPIENT_NOT_CONNECTED,
    RECIPIENT_NOT_CONNECTED_2,
    THE_OTHER_USER_LOGGED_OUT,
    THIS_ID_ALREADY_IN_USE,
)
from confy_addons.prefixes import SYSTEM_ERROR_PREFIX, SYSTEM_PREFIX
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status

from server.db import redis_client
from server.hasher import hash_id
from server.logger import logger
from server.schemas.ws import RecipientAvailabilitySchema

router = APIRouter(prefix='/ws', tags=['WebSocket'])

# Dictionary to store active WebSocket connections in the format {user_id: websocket}
active_connections: dict[str, WebSocket] = {}

# Set of active tunnels representing pairs of users who are communicating
active_tunnels = set()

# Dictionary to store users waiting for the recipient
waiting_for: dict[str, list[str]] = {}

# Dictionary to track which users are part of each tunnel
tunnel_users: dict[frozenset, set[str]] = {}


async def cleanup_user_from_redis(user_id: str):
    """
    Remove a user from Redis and cleans up their references.

    Args:
        user_id (str): ID of the user to remove

    """
    await redis_client.srem('online_users', user_id)
    logger.info(f'User {user_id} removed from Redis.')


async def handle_user_disconnect(disconnected_user: str, tunnel_id: frozenset):
    """
    Manage the disconnection of a user, including cleanup of connections and notifications.

    Args:
        disconnected_user (str): ID of the user who disconnected
        tunnel_id (frozenset): ID of the tunnel the user was part of

    """
    # Remove the disconnected user from the active connections dictionary
    if disconnected_user in active_connections:
        del active_connections[disconnected_user]

    # Remove the user from Redis
    await cleanup_user_from_redis(disconnected_user)

    # Remove the user from the tunnel's user list
    if tunnel_id in tunnel_users:
        tunnel_users[tunnel_id].discard(disconnected_user)

        # If there are still users connected to this tunnel, notify them
        remaining_users = tunnel_users[tunnel_id].copy()
        for user_id in remaining_users:
            if user_id in active_connections:
                try:
                    await active_connections[user_id].send_text(
                        f'{SYSTEM_PREFIX} {THE_OTHER_USER_LOGGED_OUT}.'
                    )
                    await active_connections[user_id].close()

                    # Remove the remaining user from active connections
                    del active_connections[user_id]
                    # Remove the remaining user from Redis
                    await cleanup_user_from_redis(user_id)

                except Exception as e:
                    logger.error(f'Error notifying user {user_id}: {e}')
                    # Remove even if there's an error in notification
                    if user_id in active_connections:
                        del active_connections[user_id]
                    await cleanup_user_from_redis(user_id)

        # Remove the tunnel when all users have disconnected
        del tunnel_users[tunnel_id]
        if tunnel_id in active_tunnels:
            active_tunnels.remove(tunnel_id)

    # Clear the waiting list if the disconnected user was being awaited
    if disconnected_user in waiting_for:
        del waiting_for[disconnected_user]

    # Remove the user from all waiting lists where they might be
    for senders in waiting_for.values():
        if disconnected_user in senders:
            senders.remove(disconnected_user)


@router.get(
    '/check-availability/{recipient_id}',
    response_model=RecipientAvailabilitySchema,
    summary='Returns if recipient is already connected with a user',
)
async def check_recipient_availability(recipient_id: str):
    """
    Check if the recipient is available to establish a new connection.

    Args:
        recipient_id (str): ID of the desired recipient

    Returns:
        JSONResponse: Status of the user's availability

    Raises:
        HTTPException:
            - 423 if the recipient is already in an active conversation

    """
    # Hash the IDs for consistency with WebSocket
    hashed_recipient = hash_id(recipient_id)

    # Check if the recipient is online
    recipient_online = await redis_client.sismember('online_users', hashed_recipient)

    # If the recipient is online, check if they are already in a conversation
    if recipient_online and hashed_recipient in active_connections:
        # Check if the recipient is already part of any active tunnel
        for users in tunnel_users.values():
            if hashed_recipient in users and len(users) > 1:
                # The recipient is already in an active conversation
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail=DETAIL_RECIPIENT_IS_ALREADY_CHATTING,
                )

    data = {
        'recipient_online': bool(recipient_online),
        'message': MESSAGE_AVAILABLE_RECIPIENT,
    }

    return data


@router.websocket('/{sender_id}@{recipient_id}')
async def websocket_endpoint(websocket: WebSocket, sender_id: str, recipient_id: str):
    """
    Establish a WebSocket connection between two users.

    Args:
        websocket (WebSocket): The sender's WebSocket connection.
        sender_id (str): The sender's ID.
        recipient_id (str): The recipient's ID.

    """
    sender_id = hash_id(sender_id)
    recipient_id = hash_id(recipient_id)

    # Accept the WebSocket connection from the client
    await websocket.accept()

    # Check if sender and recipient are the same user
    if sender_id == recipient_id:
        await websocket.send_text(f'{SYSTEM_ERROR_PREFIX} {NOT_CONNECT_YOURSELF}.')
        await websocket.close()
        return

    # Check in Redis if the user is already connected
    is_online = await redis_client.sismember('online_users', sender_id)
    if is_online:
        await websocket.send_text(f'{SYSTEM_ERROR_PREFIX} {THIS_ID_ALREADY_IN_USE}.')
        await websocket.close()
        return  # terminates the function without registering the user again

    # Check if the recipient is already in an active conversation
    if recipient_id in active_connections:
        for tunnel_id, users in tunnel_users.items():
            if recipient_id in users and len(users) > 1:
                await websocket.send_text(
                    f'{SYSTEM_ERROR_PREFIX} O destinatário já está em uma conversa ativa.'
                )
                await websocket.close()
                return

    # Register the sender's connection as active
    active_connections[sender_id] = websocket

    # Save to Redis that the user is online
    await redis_client.sadd('online_users', sender_id)

    # Create a unique and immutable identifier for the communication tunnel
    tunnel_id = frozenset({sender_id, recipient_id})

    active_tunnels.add(tunnel_id)

    # Register the users who are part of this tunnel
    if tunnel_id not in tunnel_users:
        tunnel_users[tunnel_id] = set()
    tunnel_users[tunnel_id].add(sender_id)

    # If the recipient is also connected, add them to the tunnel
    if recipient_id in active_connections:
        tunnel_users[tunnel_id].add(recipient_id)

    logger.info(f'User {sender_id} connected.')

    # If the recipient is not yet connected, notify the sender
    if recipient_id not in active_connections:
        # Add the sender to the waiting list for the recipient
        waiting_for.setdefault(recipient_id, []).append(sender_id)

        await websocket.send_text(f'{SYSTEM_PREFIX} {RECIPIENT_NOT_CONNECTED}')

    # Check if someone was waiting for this user
    if sender_id in waiting_for:
        for waiting_sender in waiting_for[sender_id]:
            if waiting_sender in active_connections:
                await active_connections[waiting_sender].send_text(
                    f'{SYSTEM_PREFIX} {RECIPIENT_CONNECTED}'
                )
                # Add the sender who was waiting to the tunnel
                tunnel_users[tunnel_id].add(waiting_sender)
        del waiting_for[sender_id]

    try:
        while True:
            # Wait to receive a message from the sender
            message = await websocket.receive_text()

            # If the recipient is connected, forward the message
            if recipient_id in active_connections:
                await active_connections[recipient_id].send_text(message)
            else:
                # If the recipient is not connected, notify the sender
                await websocket.send_text(f'{SYSTEM_PREFIX} {RECIPIENT_NOT_CONNECTED_2}')

    # If the sender disconnects, manage cleanup appropriately
    except WebSocketDisconnect:
        logger.info(f'User {sender_id} disconnected.')
        await handle_user_disconnect(sender_id, tunnel_id)
