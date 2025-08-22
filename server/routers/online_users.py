from fastapi import APIRouter, HTTPException, status

from server.db import redis_client
from server.hasher import hash_id
from server.schemas.message import Message

router = APIRouter(prefix='/online-users', tags=['Online Users'])


@router.get(
    '/{user_id}',
    response_model=Message,
    summary='Verifica se o nome de usuário solicitado está disponível.',
)
async def check_username_availability(user_id: str):
    """
    Verifica a disponibilidade de um nome de usuário no sistema.

    Este endpoint consulta o banco de dados Redis para determinar se o usuário
    especificado já está registrado como "online". Caso o usuário esteja em uso,
    a API retorna um erro de conflito (HTTP 409). Caso contrário, confirma que
    o nome está disponível.

    Args:
        user_id (str): O identificador único do usuário que se deseja verificar.

    Raises:
        HTTPException: Retorna um erro 409 (Conflict) se o nome de usuário já
        estiver em uso no momento.

    Returns:
        Message: Um objeto contendo uma mensagem informando que o nome de usuário
        está disponível.

    """
    is_online = await redis_client.sismember('online_users', hash_id(user_id))

    if is_online:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail='Este nome de usuário não está disponível'
        )

    return {'message': 'O nome de usuário está disponível'}
