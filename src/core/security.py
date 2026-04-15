from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from src.core.config import settings

# Configuração para hash de senhas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configurações para JWT
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Cria um token de acesso JWT.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    """
    Verifica a validade de um token JWT e retorna seu payload.
    Levanta HTTPException se o token for inválido ou expirar.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise credentials_exception

def get_password_hash(password: str):
    """
    Gera o hash de uma senha.
    """
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    """
    Verifica se uma senha em texto plano corresponde a um hash.
    """
    return pwd_context.verify(plain_password, hashed_password)