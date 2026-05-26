import httpx
from src.core.config import settings

HEADERS = {
    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
}


class BugsRepository:
    table = "bugs"

    async def criar(self, payload: dict):
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.SUPABASE_URL}/rest/v1/{self.table}",
                headers={**HEADERS, "Prefer": "return=representation"},
                json=payload,
            )
        return resp

    async def atualizar_status(self, bug_id: int, status: str):
        async with httpx.AsyncClient() as client:
            resp = await client.patch(
                f"{settings.SUPABASE_URL}/rest/v1/{self.table}",
                headers={**HEADERS, "Prefer": "return=representation"},
                params={"id": f"eq.{bug_id}"},
                json={"status": status},
            )
        return resp

    async def listar_paginado(
        self,
        page: int,
        per_page: int,
        filtro_status: str | None = None,
        dt_inicio: str | None = None,
        dt_fim: str | None = None,
    ):
        offset = (page - 1) * per_page

        params: dict = {
            "select": "*",
            "order": "created_at.desc",
        }

        if filtro_status:
            params["status"] = f"eq.{filtro_status}"
        if dt_inicio:
            params["created_at"] = f"gte.{dt_inicio}"
        if dt_fim:
            # Se já existe created_at (dt_inicio), o Supabase aceita múltiplos
            # params com mesmo nome via lista — usamos chave distinta com lte
            params["created_at"] = f"lte.{dt_fim}T23:59:59"

        # Quando ambos os filtros de data estão presentes, precisamos passar
        # os dois como parâmetros separados na query string
        async with httpx.AsyncClient() as client:
            request_params = list(params.items())

            if dt_inicio and dt_fim:
                # Remove o created_at inserido acima e adiciona os dois corretamente
                request_params = [(k, v) for k, v in request_params if k != "created_at"]
                request_params.append(("created_at", f"gte.{dt_inicio}"))
                request_params.append(("created_at", f"lte.{dt_fim}T23:59:59"))
            elif dt_inicio:
                request_params = [(k, v) for k, v in request_params if k != "created_at"]
                request_params.append(("created_at", f"gte.{dt_inicio}"))
            elif dt_fim:
                request_params = [(k, v) for k, v in request_params if k != "created_at"]
                request_params.append(("created_at", f"lte.{dt_fim}T23:59:59"))

            resp = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/{self.table}",
                headers={
                    **HEADERS,
                    "Range": f"{offset}-{offset + per_page - 1}",
                    "Prefer": "count=exact",
                },
                params=request_params,
            )
        return resp

    async def upload_print(self, file_bytes: bytes, filename: str, content_type: str) -> str:
        """
        Faz upload da imagem no bucket 'prints' do Supabase Storage
        e retorna a URL pública do arquivo.
        """
        path = f"{filename}"
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.SUPABASE_URL}/storage/v1/object/prints/{path}",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                    "Content-Type": content_type,
                },
                content=file_bytes,
            )

        if resp.status_code not in (200, 201):
            raise Exception(f"Erro ao fazer upload do print: {resp.text}")

        url = (
            f"{settings.SUPABASE_URL}/storage/v1/object/public/prints/{path}"
        )
        return url

    async def listar_todos_para_exportacao(self):
        """
        Retorna todos os registros de bugs sem paginação para exportação CSV.
        """
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/{self.table}",
                headers={**HEADERS, "Accept": "application/json"},
                params={
                    "select": "*",
                    "order": "created_at.desc",
                },
            )
        return resp

bugs_repository = BugsRepository()