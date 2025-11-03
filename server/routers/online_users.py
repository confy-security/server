from confy_addons.http_messages import DETAIL_USERNAME_NOT_AVAILABLE, MESSAGE_USERNAME_AVAILABLE
from fastapi import APIRouter, HTTPException, status

from server.db import redis_client
from server.hasher import hash_id
from server.schemas.message import Message

router = APIRouter(prefix='/online-users', tags=['Online Users'])


@router.get(
    '/{user_id}',
    response_model=Message,
    summary='Checks if the requested username is available.',
)
async def check_username_availability(user_id: str):
    """
    Check the availability of a username in the system.

    This endpoint queries the Redis database to determine whether the specified
    user is already registered as "online". If the username is in use, the API
    returns a conflict error (HTTP 409). Otherwise, it confirms that the
    username is available.

    Args:
        user_id (str): The unique identifier of the user to be verified.

    Raises:
        HTTPException: Returns a 409 error (Conflict) if the username is
        already in use at that moment.

    Returns:
        Message: An object containing a message informing that the username
        is available.

    """
    is_online = await redis_client.sismember('online_users', hash_id(user_id))  # type: ignore

    if is_online:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=DETAIL_USERNAME_NOT_AVAILABLE)

    return {'message': MESSAGE_USERNAME_AVAILABLE}
