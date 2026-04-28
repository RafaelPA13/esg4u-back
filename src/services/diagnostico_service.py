import csv
import io
from src.repository.pergunta_repository import pergunta_repository


class DiagnosticoService:

    async def criar_pergunta(self, payload: dict):
        # Verifica se o índice já está em uso
        check = await pergunta_repository.buscar_por_indice(payload["indice"])
        if check.status_code == 200 and check.json():
            return {"status": 409, "erro": "Pergunta já cadastrada nesse índice"}

        response = await pergunta_repository.criar(payload)
        if response.status_code in (200, 201):
            return {"status": 201, "sucesso": "Pergunta adicionada"}

        response.raise_for_status()

    async def listar_perguntas(self):
        response = await pergunta_repository.listar_todas()
        if response.status_code not in (200, 206):
            response.raise_for_status()

        data = response.json()
        if not data:
            return {"status": 204, "sucesso": "Nenhum registro encontrado"}

        return {"status": 200, "data": data}

    async def buscar_pergunta(self, pergunta_id: int):
        response = await pergunta_repository.buscar_por_id(pergunta_id)
        if response.status_code not in (200, 206):
            response.raise_for_status()

        data = response.json()
        if not data:
            return {"status": 204, "sucesso": "Nenhum registro encontrado"}

        return {"status": 200, "data": data[0]}

    async def atualizar_pergunta(self, pergunta_id: int, payload: dict):
        # Busca o registro atual para saber o índice atual
        atual_res = await pergunta_repository.buscar_por_id(pergunta_id)
        if not atual_res.json():
            return {"status": 404, "erro": "Pergunta não encontrada"}

        atual = atual_res.json()[0]
        indice_atual = atual["indice"]
        novo_indice = payload.get("indice", indice_atual)

        # Se o índice mudou, faz a troca (swap) com quem tem o novo índice
        if novo_indice != indice_atual:
            conflito_res = await pergunta_repository.buscar_por_indice(novo_indice)
            conflito_data = conflito_res.json()

            if conflito_data:
                # Troca os índices entre os dois registros
                conflito_id = conflito_data[0]["id"]
                await pergunta_repository.atualizar_indice(conflito_id, indice_atual)

        # Atualiza o registro principal com o payload completo
        response = await pergunta_repository.atualizar(pergunta_id, payload)
        if response.status_code in (200, 204):
            return {"status": 200, "sucesso": "Pergunta atualizada"}

        response.raise_for_status()

    async def deletar_pergunta(self, pergunta_id: int):
        # Busca o índice do registro a ser deletado
        atual_res = await pergunta_repository.buscar_por_id(pergunta_id)
        atual_data = atual_res.json()
        if not atual_data:
            return {"status": 404, "erro": "Pergunta não encontrada"}

        indice_deletado = atual_data[0]["indice"]

        # Deleta o registro
        response = await pergunta_repository.deletar(pergunta_id)
        if response.status_code not in (200, 204):
            response.raise_for_status()

        # Reordena os registros com índice maior que o deletado
        maiores_res = await pergunta_repository.listar_com_indice_maior_que(indice_deletado)
        maiores = maiores_res.json()

        for registro in maiores:
            await pergunta_repository.atualizar_indice(
                registro["id"],
                registro["indice"] - 1
            )

        return {"status": 204, "sucesso": "Pergunta removida"}

    async def exportar_csv(self):
        response = await pergunta_repository.listar_todas()
        if response.status_code not in (200, 206):
            response.raise_for_status()

        data = response.json()
        if not data:
            return None

        output = io.StringIO()
        fieldnames = ["id", "indice", "ativa", "eixo_esg", "tema", "pergunta", "exemplo", "created_at"]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(data)
        output.seek(0)

        return output.getvalue()


diagnostico_service = DiagnosticoService()