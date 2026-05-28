import re
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from uuid import UUID

class CadastroSchema(BaseModel):
    nome: str
    email: EmailStr
    estado: str
    cidade: str
    senha: str
    confirmar_senha: str

    @field_validator("senha")
    def validar_senha(cls, v):
        if len(v) < 8:
            raise ValueError("Senha deve ter no mínimo 8 caracteres")

        if not re.search(r"[A-Z]", v):
            raise ValueError("Senha deve ter letra maiúscula")

        if not re.search(r"[a-z]", v):
            raise ValueError("Senha deve ter letra minúscula")

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Senha deve ter caractere especial")

        return v
    
class LoginSchema(BaseModel):
    email: str
    senha: str
    
class UserResponseSchema(BaseModel):
    id: UUID
    nome: str
    email: EmailStr
    score_esg: Optional[float] = 0
    reputacao: Optional[int] = 0
    admin: bool = False

    class Config:
        from_attributes = True # Para compatibilidade com ORM/dict

class UserUpdateSchema(BaseModel):
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    score_esg: Optional[float] = None
    reputacao: Optional[int] = None
    admin: Optional[bool] = None
    estado: Optional[str] = None
    cidade: Optional[str] = None
    grau_escolaridade: Optional[str] = None
    faixa_etaria: Optional[str] = None
    situacao_profissional: Optional[str] = None
    tipo_moradia: Optional[str] = None
    pessoas_familia: Optional[str] = None
    foto_perfil: Optional[str] = None

class UserAprovadorSchema(BaseModel):
    id: UUID
    nome: str
    email: EmailStr

    class Config:
        from_attributes = True