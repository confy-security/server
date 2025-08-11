"""Confy Server -  Servidor web de encaminhamento de mensagens enviadas por aplicativos clientes compatíveis."""

from fastapi import FastAPI

from server.routers import status, ws

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

app.include_router(ws.router)
app.include_router(status.router)
