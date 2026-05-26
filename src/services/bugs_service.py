import io
import csv
from datetime import datetime
from zoneinfo import ZoneInfo

from src.repository.bugs_repository import bugs_repository


class BugsService:

    async def reportar_bug(self, user_id: str, titulo: str, descricao: str, file_bytes: bytes, filename: str, content_type: str):
        """
        POST /bugs/reportar_bug
        Salva o print no Storage e cria o registro na tabela bugs.
        """
        # RN1: Upload da imagem no bucket 'prints'
        try:
            print_url = await bugs_repository.upload_print(file_bytes, filename, content_type)
        except Exception as e:
            return {"status": 400, "erro": str(e)}

        payload = {
            "user_id": user_id,
            "titulo": titulo,
            "descricao": descricao,
            "print": print_url,
            "status": "pendente",  # RN3: sempre pendente na criação
        }

        resp = await bugs_repository.criar(payload)
        if resp.status_code not in (200, 201):
            return {"status": resp.status_code, "erro": resp.text}

        return {"status": 201, "sucesso": "Bug reportado ao administrador"}

    async def atualizar_status(self, bug_id: int, novo_status: str):
        """
        PUT /bugs/{id}
        Atualiza o status de um bug.
        """
        resp = await bugs_repository.atualizar_status(bug_id, novo_status)
        if resp.status_code not in (200, 204):
            return {"status": resp.status_code, "erro": resp.text}

        return {"status": 200, "sucesso": "Bug resolvido"}

    async def listar(
        self,
        page: int,
        per_page: int,
        filtro_status: str | None = None,
        dt_inicio: str | None = None,
        dt_fim: str | None = None,
    ):
        """
        GET /bugs/listar
        Lista paginada de bugs com filtros opcionais.
        """
        resp = await bugs_repository.listar_paginado(
            page=page,
            per_page=per_page,
            filtro_status=filtro_status,
            dt_inicio=dt_inicio,
            dt_fim=dt_fim,
        )

        if resp.status_code not in (200, 206):
            return {"status": resp.status_code, "erro": resp.text}

        bugs_raw = resp.json() or []

        # Extrai total do header Content-Range
        content_range = resp.headers.get("content-range", "")
        try:
            total = int(content_range.split("/")[1])
        except (IndexError, ValueError):
            total = len(bugs_raw)

        if not bugs_raw:
            return {"status": 204, "sucesso": "Nenhum bug encontrado"}

        # Formata created_at para dd/MM/yyyy HH:mm
        bugs_formatados = []
        for b in bugs_raw:
            try:
                dt = datetime.fromisoformat(b["created_at"])
                timezone_br = ZoneInfo("America/Sao_Paulo")
                dt_formatado = dt.astimezone(timezone_br).strftime("%d/%m/%Y %H:%M")
            except Exception as e:
                print("ERRO AO FORMATAR DATA:", e)
                dt_formatado = b["created_at"]

            bugs_formatados.append({
                "id": b["id"],
                "user_id": b["user_id"],
                "titulo": b["titulo"],
                "descricao": b["descricao"],
                "print": b["print"],
                "status": b["status"],
                "created_at": dt_formatado,
            })

        pages = max(1, -(-total // per_page))

        return {
            "status": 200,
            "data": {
                "bugs": bugs_formatados,
                "registros": total,
                "pages": pages,
                "page": page,
                "per_page": per_page,
                "prox_page": page < pages,
                "prev_page": page > 1,
            },
        }

    async def exportar_csv(self):
        """
        GET /bugs/exportar_csv
        Exporta todos os registros de bugs em CSV.
        """
        resp = await bugs_repository.listar_todos_para_exportacao()
        if resp.status_code not in (200, 206):
            return None

        bugs = resp.json() or []
        if not bugs:
            return None

        output = io.StringIO()
        fieldnames = ["id", "user_id", "titulo", "descricao", "print", "status", "created_at"]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        for b in bugs:
            try:
                dt = datetime.fromisoformat(b["created_at"].replace("Z", "+00:00"))
                timezone_br = ZoneInfo("America/Sao_Paulo")
                b["created_at"] = dt.astimezone(timezone_br).strftime("%d/%m/%Y %H:%M")
            except Exception:
                pass
            writer.writerow(b)

        output.seek(0)
        return output.getvalue()

bugs_service = BugsService()