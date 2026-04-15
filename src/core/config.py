import os
from dotenv import load_dotenv

load_dotenv() # Carrega as variáveis do arquivo .env

class Settings:
    # Supabase API (para acesso RESTful)
    SUPABASE_URL: str = os.getenv("SUPABASE_URL")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY") # Chave anon (publica)
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY") # Chave de serviço (para operações privilegiadas)

    # JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 180))

    # Resend
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY")
    EMAIL_FROM: str = os.getenv("EMAIL_FROM")

settings = Settings()