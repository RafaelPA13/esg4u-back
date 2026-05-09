import asyncio
import io
import csv
from datetime import date
from math import ceil
from src.repository.convites_repository import convites_repository
from src.repository.user_repository import user_repository
from src.services.email_service import email_service


class ConvitesService:

    async def enviar_convite(self, remetente_id: str, remetente_nome: str, destinatario_email: str):
        # 1. Buscar template de e-mail de convite
        template_data = await user_repository.get_template_by_name("template_email_convite")

        if not template_data or len(template_data) == 0:
            return {"status": 400, "erro": "Template de email de convite não encontrado"}

        template = template_data[0].get("conteudo", "")

        # 2. Substituir campos dinâmicos no template
        html = template.replace("{{NOME_REMETENTE}}", remetente_nome)

        # 3. Enviar e-mail (não bloqueante)
        try:
            asyncio.create_task(
                asyncio.to_thread(
                    email_service.send_email,
                    destinatario_email,
                    "Você foi convidado para o ESG4U!",
                    html,
                )
            )
        except Exception as e:
            return {"status": 400, "erro": f"Erro ao enviar convite por e-mail: {e}"}

        # 4. Adicionar registro na tabela convites
        res_convite = await convites_repository.criar(remetente_id, destinatario_email)
        if res_convite.status_code not in (200, 201):
            res_convite.raise_for_status() # Levanta exceção se houver erro no Supabase

        return {"status": 201, "sucesso": "Convite enviado por e-mail"}

    async def listar_convites_por_remetente(self, remetente_id: str, page: int, per_page: int, filtros: dict):
        response = await convites_repository.listar_por_remetente(remetente_id, page, per_page, filtros)

        if response.status_code == 204:
            return {"status": 204, "sucesso": "Nenhum registro encontrado"}
        if response.status_code != 200:
            response.raise_for_status()

        convites_data = response.json()
        total_registros = int(response.headers.get("Content-Range").split("/")[1])
        total_pages = ceil(total_registros / per_page) if total_registros > 0 else 1

        # Contar pendentes e convertidos
        pendentes_res = await convites_repository.contar_por_status(remetente_id, "Pendente")
        convertidos_res = await convites_repository.contar_por_status(remetente_id, "Convertido")

        pendentes = int(pendentes_res.headers.get("Content-Range").split("/")[1]) if pendentes_res.status_code == 200 else 0
        convertidos = int(convertidos_res.headers.get("Content-Range").split("/")[1]) if convertidos_res.status_code == 200 else 0

        formatted_convites = []
        for convite in convites_data:
            formatted_convites.append({
                "id_convite": convite["id"],
                "remetente": convite["remetente"],
                "destinatario": convite["destinatario"],
                "status": convite["status"],
                "dt_envio": date.fromisoformat(convite["dt_envio"]).strftime("%d/%m/%Y"),
            })

        return {
            "status": 200,
            "data": {
                "convites": formatted_convites,
                "registros": total_registros,
                "convertidos": convertidos,
                "pendentes": pendentes,
                "page": page,
                "pages": total_pages,
                "per_page": per_page,
                "prev_page": page > 1,
                "prox_page": page < total_pages,
            },
        }

    async def listar_todos_convites(self, page: int, per_page: int, filtros: dict):
        response = await convites_repository.listar_todos(page, per_page, filtros)

        if response.status_code == 204:
            return {"status": 204, "sucesso": "Nenhum registro encontrado"}
        if response.status_code != 200:
            response.raise_for_status()

        convites_data = response.json()
        total_registros = int(response.headers.get("Content-Range").split("/")[1])
        total_pages = ceil(total_registros / per_page) if total_registros > 0 else 1

        formatted_convites = []
        for convite in convites_data:
            formatted_convites.append({
                "id_convite": convite["id"],
                "remetente": convite["remetente"],
                "destinatario": convite["destinatario"],
                "status": convite["status"],
                "dt_envio": date.fromisoformat(convite["dt_envio"]).strftime("%d/%m/%Y"),
            })

        return {
            "status": 200,
            "data": {
                "convites": formatted_convites,
                "registros": total_registros,
                "page": page,
                "pages": total_pages,
                "per_page": per_page,
                "prev_page": page > 1,
                "prox_page": page < total_pages,
            },
        }

    async def atualizar_status_convite_por_email(self, destinatario_email: str, novo_status: str):
        response = await convites_repository.buscar_por_destinatario(destinatario_email)
        if response.status_code == 200 and response.json():
            for convite in response.json():
                if convite["status"] != novo_status: # Evita atualizar se já estiver no status desejado
                    await convites_repository.atualizar_status(convite["id"], novo_status)
            return {"sucesso": True}
        return {"sucesso": False}

    async def exportar_convites_csv(self):
        """
        Busca todos os convites e gera um CSV em memória.
        """
        response = await convites_repository.listar_todos_para_exportar()

        if response.status_code not in (200, 206):
            response.raise_for_status()

        convites_data = response.json()

        if not convites_data:
            return None

        output = io.StringIO()
        fieldnames = ["id", "remetente", "destinatario", "status", "dt_envio", "created_at"]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        # Formatar dt_envio e created_at para o CSV
        formatted_data = []
        for convite in convites_data:
            convite_copy = convite.copy()
            if "dt_envio" in convite_copy and convite_copy["dt_envio"]:
                convite_copy["dt_envio"] = date.fromisoformat(convite_copy["dt_envio"]).strftime("%d/%m/%Y")
            if "created_at" in convite_copy and convite_copy["created_at"]:
                # created_at é um timestamp com timezone, precisa de tratamento mais robusto se quiser formatar
                # Por simplicidade, vou apenas pegar a data, mas pode ser ajustado
                convite_copy["created_at"] = date.fromisoformat(convite_copy["created_at"].split("T")[0]).strftime("%d/%m/%Y %H:%M:%S")
            formatted_data.append(convite_copy)

        writer.writerows(formatted_data)
        output.seek(0)

        return output.getvalue()
    
convites_service = ConvitesService()