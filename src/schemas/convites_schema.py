from pydantic import BaseModel, EmailStr
from datetime import date


class EnviarConviteSchema(BaseModel):
    email: EmailStr


class ConviteResponse(BaseModel):
    id: int
    remetente: str
    destinatario: EmailStr
    status: str
    dt_envio: date