"""Confy Server -  Servidor web de encaminhamento de mensagens enviadas por aplicativos clientes compatíveis."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from server.db import redis_client
from server.routers import online_users, status, ws

description = """
Este servidor realiza o encaminhamento de mensagens entre usuários conectados
via WebSocket utilizando algum aplicativo cliente compatível com o servidor.
"""


@asynccontextmanager
async def clean_online_users(app: FastAPI):
    """
    Gerencia o ciclo de vida da aplicação FastAPI garantindo a limpeza dos usuários online.

    Este gerenciador de contexto é executado quando a aplicação inicia e termina.
    Ao encerrar o ciclo de vida da aplicação, remove do Redis todos os registros
    de usuários que estavam marcados como "online", evitando que conexões antigas
    permaneçam ativas indevidamente após um restart do servidor.

    Args:
        app (FastAPI): Instância da aplicação FastAPI.

    Yields:
        None: Permite a execução normal da aplicação durante o ciclo de vida.

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
