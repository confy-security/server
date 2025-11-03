"""Confy Server - Web server for forwarding messages sent by compatible client applications."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from server.db import redis_client
from server.routers import online_users, status, ws

description = """
This server forwards messages between users connected via WebSocket
using a compatible client application.
"""


@asynccontextmanager
async def clean_online_users(app: FastAPI):
    """
    Manage the FastAPI application lifecycle ensuring cleanup of online users.

    This context manager is executed when the application starts and terminates.
    Upon terminating the application lifecycle, it removes from Redis all records
    of users marked as "online", preventing old connections from remaining active
    unintentionally after a server restart.

    Args:
        app (FastAPI): Instance of the FastAPI application.

    Yields:
        None: Allows normal execution of the application during the lifecycle.

    """
    yield
    await redis_client.delete('online_users')


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
    lifespan=clean_online_users,
)

app.include_router(ws.router)
app.include_router(status.router)
app.include_router(online_users.router)
