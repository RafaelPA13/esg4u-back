import httpx
from src.core.config import settings


class PerguntaRepository:

    async def criar(self, payload: dict):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.SUPABASE_URL}/rest/v1/perguntas",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation",
                },
                json=payload,
            )
        return response

    async def buscar_por_indice(self, indice: int):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/perguntas",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                    "Accept": "application/json",
                },
                params={"indice": f"eq.{indice}", "select": "*"},
            )
        return response

    async def listar_todas(self):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/perguntas",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                    "Accept": "application/json",
                },
                params={"select": "*", "order": "indice.asc"},
            )
        return response

    async def buscar_por_id(self, pergunta_id: int):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/perguntas",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                    "Accept": "application/json",
                },
                params={"id": f"eq.{pergunta_id}", "select": "*"},
            )
        return response

    async def atualizar(self, pergunta_id: int, payload: dict):
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{settings.SUPABASE_URL}/rest/v1/perguntas",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation",
                },
                params={"id": f"eq.{pergunta_id}"},
                json=payload,
            )
        return response

    async def atualizar_indice(self, pergunta_id: int, novo_indice: int):
        """Atualiza apenas o índice de um registro específico."""
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{settings.SUPABASE_URL}/rest/v1/perguntas",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                    "Content-Type": "application/json",
                },
                params={"id": f"eq.{pergunta_id}"},
                json={"indice": novo_indice},
            )
        return response

    async def deletar(self, pergunta_id: int):
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{settings.SUPABASE_URL}/rest/v1/perguntas",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                },
                params={"id": f"eq.{pergunta_id}"},
            )
        return response

    async def listar_com_indice_maior_que(self, indice: int):
        """Busca todos os registros com índice maior que o informado para reordenação."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/perguntas",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                    "Accept": "application/json",
                },
                params={
                    "indice": f"gt.{indice}",
                    "select": "id,indice",
                    "order": "indice.asc",
                },
            )
        return response


pergunta_repository = PerguntaRepository()