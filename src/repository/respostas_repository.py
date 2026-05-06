# src/repository/respostas_repository.py

import httpx
from src.core.config import settings


class RespostaRepository:
    async def upsert_lote(self, registros: list):
        """
        Insere ou atualiza múltiplas respostas via upsert, usando a UNIQUE
        (respondido_por, id_pergunta) como chave de conflito.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.SUPABASE_URL}/rest/v1/respostas_perguntas",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "resolution=merge-duplicates,return=representation",
                },
                params={
                    "on_conflict": "respondido_por,id_pergunta",
                },
                json=registros,
            )
        return response

    async def listar_por_usuario(self, usuario_id: str):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/respostas_perguntas",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                    "Accept": "application/json",
                },
                params={
                    "respondido_por": f"eq.{usuario_id}",
                    "select": "id,id_pergunta,pontuacao",
                },
            )
        return response

    async def listar_por_usuario_e_pergunta(self, usuario_id: str, id_pergunta: int):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/respostas_perguntas",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                    "Accept": "application/json",
                },
                params={
                    "respondido_por": f"eq.{usuario_id}",
                    "id_pergunta": f"eq.{id_pergunta}",
                    "select": "id,pontuacao",
                },
            )
        return response

    async def buscar_por_id(self, resposta_id: int):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/respostas_perguntas",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                    "Accept": "application/json",
                },
                params={
                    "id": f"eq.{resposta_id}",
                    "select": "id,id_pergunta,pontuacao",
                },
            )
        return response

resposta_repository = RespostaRepository()