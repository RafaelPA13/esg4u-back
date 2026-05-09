import httpx
from src.core.config import settings
from datetime import date

HEADERS = {
    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
}


class ConvitesRepository:

    async def criar(self, remetente_id: str, destinatario_email: str):
        payload = {
            "remetente": remetente_id,
            "destinatario": destinatario_email,
            "status": "Pendente",
            "dt_envio": date.today().isoformat(),
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.SUPABASE_URL}/rest/v1/convites",
                headers={**HEADERS, "Prefer": "return=representation"},
                json=payload,
            )
        return response

    async def listar_por_remetente(self, remetente_id: str, page: int, per_page: int, filtros: dict):
        offset = (page - 1) * per_page
        params = {
            "remetente": f"eq.{remetente_id}",
            "select": "id,remetente,destinatario,status,dt_envio",
            "offset": offset,
            "limit": per_page,
            "order": "dt_envio.desc",
        }
        for key, value in filtros.items():
            params[key] = f"eq.{value}"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/convites",
                headers={**HEADERS, "Prefer": "count=exact"},
                params=params,
            )
        return response

    async def listar_todos(self, page: int, per_page: int, filtros: dict):
        offset = (page - 1) * per_page
        params = {
            "select": "id,remetente,destinatario,status,dt_envio",
            "offset": offset,
            "limit": per_page,
            "order": "dt_envio.desc",
        }
        for key, value in filtros.items():
            params[key] = f"eq.{value}"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/convites",
                headers={**HEADERS, "Prefer": "count=exact"},
                params=params,
            )
        return response

    async def contar_por_status(self, remetente_id: str, status: str):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/convites",
                headers={**HEADERS, "Prefer": "count=exact"},
                params={
                    "remetente": f"eq.{remetente_id}",
                    "status": f"eq.{status}",
                    "select": "count",
                },
            )
        return response

    async def buscar_por_destinatario(self, destinatario_email: str):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/convites",
                headers=HEADERS,
                params={
                    "destinatario": f"eq.{destinatario_email}",
                    "select": "id,status",
                },
            )
        return response

    async def atualizar_status(self, convite_id: int, novo_status: str):
        payload = {"status": novo_status}
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{settings.SUPABASE_URL}/rest/v1/convites",
                headers={**HEADERS, "Prefer": "return=representation"},
                params={"id": f"eq.{convite_id}"},
                json=payload,
            )
        return response


    async def listar_todos_para_exportar(self):
        """
        Lista todos os convites sem paginação ou filtros para exportação.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/convites",
                headers=HEADERS,
                params={
                    "select": "id,remetente,destinatario,status,dt_envio,created_at",
                    "order": "dt_envio.desc",
                },
            )
        return response
convites_repository = ConvitesRepository()