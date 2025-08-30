from pydantic import BaseModel


class RecipientAvailabilitySchema(BaseModel):
    recipient_online: bool
    message: str
