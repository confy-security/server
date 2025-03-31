from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from server.logger import logger

app = FastAPI(title='Confy Server')

active_connections: dict[str, WebSocket] = {}
active_tunnels = set()


@app.websocket('/ws/{sender_id}@{recipient_id}')
async def websocket_endpoint(websocket: WebSocket, sender_id: str, recipient_id: str):
    await websocket.accept()

    active_connections[sender_id] = websocket

    tunnel_id = frozenset({sender_id, recipient_id})

    if not active_tunnels:
        active_tunnels.add(tunnel_id)
    else:
        for id in active_tunnels.copy():
            if tunnel_id == id:
                break
            elif recipient_id not in id:
                active_tunnels.add(tunnel_id)
                break
        else:
            await websocket.send_text(f'SERVER: User {recipient_id} is unavailable.')
            await websocket.close()
            logger.warning(
                f'User {sender_id} tried to talk '
                'to user {recipient_id} who is unavailable.'
            )

    logger.info(f'User {sender_id} connected.')

    try:
        while True:
            message = await websocket.receive_text()

            if recipient_id in active_connections:
                await active_connections[recipient_id].send_text(message)
            else:
                logger.warning(f'Message to {recipient_id} failed: user not connected')

    except WebSocketDisconnect:
        if sender_id in active_connections:
            del active_connections[sender_id]

        if recipient_id in active_connections:
            recipient_connection = active_connections[recipient_id]

            await recipient_connection.send_text('The other user has disconnected.')

            await recipient_connection.close()
            del active_connections[recipient_id]

        if tunnel_id in active_tunnels:
            active_tunnels.remove(tunnel_id)

        logger.info(f'User {sender_id} disconnected.')
