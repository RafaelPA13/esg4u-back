import httpx
from src.core.config import settings

HEADERS = {
    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
}


class EvidenciasRepository:

    async def criar(self, payload: dict):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.SUPABASE_URL}/rest/v1/evidencias",
                headers={**HEADERS, "Prefer": "return=representation"},
                json=payload,
            )
        return response

    async def buscar_por_id(self, evidencia_id: int):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/evidencias",
                headers=HEADERS,
                params={
                    "id": f"eq.{evidencia_id}",
                    "select": "id,id_resposta,evidencia,pontuacao,created_at",
                },
            )
        return response

    async def buscar_por_resposta(self, id_resposta: int):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/evidencias",
                headers=HEADERS,
                params={
                    "id_resposta": f"eq.{id_resposta}",
                    "select": "id,id_resposta,evidencia,pontuacao,created_at",
                },
            )
        return response
    
    async def listar_por_respostas(self, ids_respostas: list[int]):
        """Retorna evidências cujo id_resposta está na lista fornecida."""
        if not ids_respostas:
            # Retorna um objeto httpx.Response vazio para manter o padrão
            return httpx.Response(200, json=[])

        ids_str = ",".join(str(i) for i in ids_respostas)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/evidencias",
                headers=HEADERS,
                params={
                    "id_resposta": f"in.({ids_str})",
                    "select": "id,id_resposta,evidencia,pontuacao,created_at",
                },
            )
        return response

    async def atualizar_pontuacao(self, evidencia_id: int, nova_pontuacao: float):
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{settings.SUPABASE_URL}/rest/v1/evidencias",
                headers={**HEADERS, "Prefer": "return=representation"},
                params={"id": f"eq.{evidencia_id}"},
                json={"pontuacao": nova_pontuacao},
            )
        return response

    async def listar_ids_respostas_com_evidencia(self, ids_respostas: list):
        """Retorna evidências cujo id_resposta está na lista fornecida."""
        ids_str = ",".join(str(i) for i in ids_respostas)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/evidencias",
                headers=HEADERS,
                params={
                    "id_resposta": f"in.({ids_str})",
                    "select": "id,id_resposta,evidencia,pontuacao,created_at",
                },
            )
        return response


evidencias_repository = EvidenciasRepository()