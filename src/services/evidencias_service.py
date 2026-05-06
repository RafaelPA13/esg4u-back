from src.repository.evidencias_repository import evidencias_repository
from src.repository.respostas_repository import resposta_repository
from src.repository.pergunta_repository import pergunta_repository
from src.repository.user_repository import user_repository
from src.core.config import settings
import httpx


class EvidenciasService:

    # helpers internos

    def _montar_item(self, pergunta: dict, resposta: dict, evidencia: dict | None) -> dict:
        return {
            "id_pergunta": pergunta["id"],
            "pergunta": pergunta["pergunta"],
            "resposta": {
                "id_resposta": resposta["id"],
                "pontuacao": resposta["pontuacao"],
            },
            "evidencia": {
                "id_evidencia": evidencia["id"],
                "evidencia": evidencia["evidencia"],
                "pontuacao": evidencia["pontuacao"],
                "dt_postagem": evidencia["created_at"],
            } if evidencia else None,
        }

    # GET /evidencias/minhas-evidencias

    async def listar_minhas_evidencias(self, usuario_id: str):
        # 1. Busca todas as respostas do usuário
        res_respostas = await resposta_repository.listar_por_usuario(usuario_id)
        if res_respostas.status_code != 200:
            res_respostas.raise_for_status()

        respostas = res_respostas.json()
        if not respostas:
            return {"status": 200, "data": []}

        # 2. Busca todas as perguntas ativas ordenadas por índice
        res_perguntas = await pergunta_repository.listar_todas()
        if res_perguntas.status_code not in (200, 206):
            res_perguntas.raise_for_status()

        perguntas = res_perguntas.json()

        # Mapa id_pergunta -> pergunta
        mapa_perguntas = {p["id"]: p for p in perguntas}
        # Mapa id_pergunta -> resposta
        mapa_respostas = {r["id_pergunta"]: r for r in respostas}

        # 3. Busca evidências para as respostas existentes
        ids_respostas = [r["id"] for r in respostas]
        mapa_evidencias = {}
        if ids_respostas:
            res_evid = await evidencias_repository.listar_ids_respostas_com_evidencia(
                ids_respostas
            )
            if res_evid.status_code == 200:
                for e in res_evid.json():
                    mapa_evidencias[e["id_resposta"]] = e

        # 4. Monta lista ordenada por índice da pergunta
        resultado = []
        for pergunta in sorted(perguntas, key=lambda p: p.get("indice", 0)):
            pid = pergunta["id"]
            if pid not in mapa_respostas:
                continue
            resposta = mapa_respostas[pid]
            evidencia = mapa_evidencias.get(resposta["id"])
            resultado.append(self._montar_item(pergunta, resposta, evidencia))

        return {"status": 200, "data": resultado}

    # GET /evidencias/{id}

    async def buscar_evidencia(self, evidencia_id: int):
        res_evid = await evidencias_repository.buscar_por_id(evidencia_id)
        if res_evid.status_code != 200:
            res_evid.raise_for_status()

        lista = res_evid.json()
        if not lista:
            return {"status": 404, "erro": "Evidência não encontrada"}

        evidencia = lista[0]

        # Busca resposta
        res_resp = await resposta_repository.buscar_por_id(evidencia["id_resposta"])
        resposta = res_resp.json()[0] if res_resp.status_code == 200 and res_resp.json() else {}

        # Busca pergunta
        res_perg = await pergunta_repository.buscar_por_id(resposta.get("id_pergunta", 0))
        pergunta = res_perg.json()[0] if res_perg.status_code == 200 and res_perg.json() else {}

        return {
            "status": 200,
            "data": self._montar_item(pergunta, resposta, evidencia),
        }

    # POST /evidencias/adicionar

    async def adicionar_evidencia(
        self,
        id_resposta: int,
        file_bytes: bytes,
        file_name: str,
        content_type: str,
        usuario_id: str,
    ):
        # 1. Busca a resposta
        res_resp = await resposta_repository.buscar_por_id(id_resposta)
        if res_resp.status_code != 200 or not res_resp.json():
            return {"status": 404, "erro": "Resposta não encontrada"}

        resposta = res_resp.json()[0]
        pontuacao_resposta = resposta["pontuacao"]
        pontuacao_evidencia = round(pontuacao_resposta * 1.5, 2)

        # 2. Faz upload da imagem para o bucket "evidencias" no Supabase Storage
        storage_path = f"{usuario_id}/{id_resposta}_{file_name}"
        async with httpx.AsyncClient() as client:
            upload_res = await client.post(
                f"{settings.SUPABASE_URL}/storage/v1/object/evidencias/{storage_path}",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                    "Content-Type": content_type,
                    "x-upsert": "true",
                },
                content=file_bytes,
            )

        if upload_res.status_code not in (200, 201):
            return {"status": 500, "erro": "Erro ao fazer upload da imagem"}

        # 3. Monta a URL pública
        url_evidencia = (
            f"{settings.SUPABASE_URL}/storage/v1/object/public/evidencias/{storage_path}"
        )

        # 4. Salva o registro de evidência
        payload_evid = {
            "id_resposta": id_resposta,
            "evidencia": url_evidencia,
            "pontuacao": pontuacao_evidencia,
        }
        res_criar = await evidencias_repository.criar(payload_evid)
        if res_criar.status_code not in (200, 201):
            res_criar.raise_for_status()

        # 5. Recalcula score ESG do usuário
        await self._recalcular_score(usuario_id)

        return {"status": 201, "sucesso": "Evidência adicionada com sucesso"}

    # Recálculo de score 

    async def _recalcular_score(self, usuario_id: str):
        """
        Score = soma das pontuações das respostas sem evidência
              + soma das pontuações das evidências (pontuacao_resposta * 1.5)
        """
        res_respostas = await resposta_repository.listar_por_usuario(usuario_id)
        respostas = res_respostas.json() if res_respostas.status_code == 200 else []

        ids_respostas = [r["id"] for r in respostas]
        mapa_evidencias = {}
        if ids_respostas:
            res_evid = await evidencias_repository.listar_ids_respostas_com_evidencia(
                ids_respostas
            )
            if res_evid.status_code == 200:
                for e in res_evid.json():
                    mapa_evidencias[e["id_resposta"]] = e

        score_total = 0.0
        for r in respostas:
            evid = mapa_evidencias.get(r["id"])
            if evid:
                score_total += evid["pontuacao"]
            else:
                score_total += r["pontuacao"]

        await user_repository.atualizar_score_esg(usuario_id, score_total)


evidencias_service = EvidenciasService()