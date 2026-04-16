import httpx
import uuid
from src.core.config import settings
from src.db.supabase_client import supabase

class UserRepository:
    # Usuarios
    
    async def create_user(self, user_data: dict):
        response = await supabase.post(
            "/rest/v1/usuarios",
            user_data
        )
        return response

    async def find_by_email(self, email: str):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/usuarios",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                },
                params={"email": f"eq.{email}"}
            )

        return response
    
    async def find_by_id(self, user_id: str):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/usuarios",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                },
                params={"id": f"eq.{user_id}"}
            )

        return response
    
    async def delete_user(self, user_id: str):
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{settings.SUPABASE_URL}/rest/v1/usuarios",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                },
                params={"id": f"eq.{user_id}"}
            )
        return response
    
    # Template
    
    async def get_template(self):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/parametros",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                },
                params={"id": "eq.template_email_codigo"}
            )

        return response.json()
    
    # Código / Reset de senha
    
    # Criar token
    async def create_token(self, data: dict):
        return await supabase.post("/rest/v1/auth_tokens", data)

    # Buscar token por valor (usado no reset)
    async def get_token_by_valor(self, valor: str, tipo: str):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/auth_tokens",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                },
                params={
                    "codigo": f"eq.{valor}",
                    "tipo": f"eq.{tipo}",
                    "usado": "eq.false"
                }
            )
        return response

    # Buscar token por código
    async def get_token_by_codigo(self, codigo: str):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/auth_tokens",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                },
                params={
                    "codigo": f"eq.{codigo}",
                    "usado": "eq.false"
                }
            )
        return response


    # Buscar token por user + tipo
    async def get_token_by_user(self, user_id: str, tipo: str):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/auth_tokens",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                },
                params={
                    "user_id": f"eq.{user_id}",
                    "tipo": f"eq.{tipo}",
                    "usado": "eq.false"
                }
            )
        return response


    # Atualizar token (reenviar)
    async def update_token(self, token_id: str, codigo: str, expires_at: str):
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{settings.SUPABASE_URL}/rest/v1/auth_tokens",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                    "Content-Type": "application/json"
                },
                params={"id": f"eq.{token_id}"},
                json={
                    "codigo": codigo,
                    "expires_at": expires_at,
                    "usado": False
                }
            )
        return response


    # Marcar token como usado
    async def mark_token_used(self, token_id: str):
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{settings.SUPABASE_URL}/rest/v1/auth_tokens",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                    "Content-Type": "application/json"
                },
                params={"id": f"eq.{token_id}"},
                json={"usado": True}
            )
        return response

user_repository = UserRepository()