import re
from pydantic import BaseModel, EmailStr, field_validator

class CadastroSchema(BaseModel):
    nome: str
    email: EmailStr
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