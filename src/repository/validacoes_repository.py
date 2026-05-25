import httpx
from src.core.config import settings


class ValidacoesRepository:
    table = "validacoes"

    async def criar_validacao(self, payload: dict):
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.SUPABASE_URL}/rest/v1/{self.table}",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation",
                },
                json=payload,
            )
        return resp

    async def buscar_por_id(self, validacao_id: int):
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/{self.table}",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                    "Accept": "application/json",
                },
                params={"id": f"eq.{validacao_id}", "select": "*"},
            )
        return resp

    async def atualizar_validacao(self, validacao_id: int, payload: dict):
        async with httpx.AsyncClient() as client:
            resp = await client.patch(
                f"{settings.SUPABASE_URL}/rest/v1/{self.table}",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation",
                },
                params={"id": f"eq.{validacao_id}"},
                json=payload,
            )
        return resp

    async def listar_por_avaliador_email(self, avaliador_email: str):
        """
        Retorna validações onde o avaliador corresponde ao e-mail informado.
        Usado pelo GET /{avaliador_email}.
        """
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/{self.table}",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                    "Accept": "application/json",
                },
                params={
                    "avaliador": f"eq.{avaliador_email}",
                    "select": "id,validado,pontuacao,pedido_por,id_resposta",
                },
            )
        return resp

    async def listar_por_pedido_por_email(self, pedido_por_email: str):
        """
        Retorna validações onde o solicitante corresponde ao e-mail informado.
        Usado pelo GET /minhas_validacoes/{pedido_por_email}.
        """
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/{self.table}",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                    "Accept": "application/json",
                },
                params={
                    "pedido_por": f"eq.{pedido_por_email}",
                    "select": "id,validado,pontuacao,avaliador,id_resposta",
                },
            )
        return resp

    async def listar_validacoes_por_email_e_resposta(self, pedido_por_email: str, id_resposta: int):
        """
        Verifica se já existe uma validação para o e-mail + resposta informados.
        """
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/{self.table}",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                    "Accept": "application/json",
                },
                params={
                    "pedido_por": f"eq.{pedido_por_email}",
                    "id_resposta": f"eq.{id_resposta}",
                    "select": "id",
                },
            )
        return resp
    
    async def listar_resolvidas_por_respostas(self, pedido_por_email: str, ids_respostas: list[int]):
        """
        Retorna validações com validado='validado' ou 'rejeitado' (exclui 'pendente')
        para um conjunto de respostas do usuário.
        """
        if not ids_respostas:
            return httpx.Response(200, json=[])

        ids_str = ",".join(str(i) for i in ids_respostas)
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/{self.table}",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                    "Accept": "application/json",
                },
                params={
                    "pedido_por": f"eq.{pedido_por_email}",
                    "id_resposta": f"in.({ids_str})",
                    "validado": "neq.pendente",  # exclui pendentes
                    "select": "id,id_resposta,validado,pontuacao",
                },
            )
        return resp
    
    async def listar_todas_paginado(
        self,
        page: int,
        per_page: int,
        filtro_pedido_por: str | None = None,
        filtro_avaliador: str | None = None,
    ):
        """
        Retorna validações paginadas com filtros opcionais.
        pedido_por filtra por nome (ilike), avaliador filtra por email (ilike).
        """
        offset = (page - 1) * per_page

        params: dict = {
            "select": "id,validado,pontuacao,pedido_por,avaliador,id_resposta",
            "order": "created_at.desc",
        }

        if filtro_avaliador:
            params["avaliador"] = f"ilike.%{filtro_avaliador}%"

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/{self.table}",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                    "Accept": "application/json",
                    "Range": f"{offset}-{offset + per_page - 1}",
                    "Prefer": "count=exact",
                },
                params=params,
            )
        return resp

    async def listar_todas_para_exportacao(self):
        """
        Retorna todos os registros de validação sem paginação para exportação CSV.
        """
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/{self.table}",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                    "Accept": "application/json",
                },
                params={
                    "select": "id,pedido_por,avaliador,validado,pontuacao,created_at,id_resposta",
                    "order": "created_at.desc",
                },
            )
        return resp


validacoes_repository = ValidacoesRepository()