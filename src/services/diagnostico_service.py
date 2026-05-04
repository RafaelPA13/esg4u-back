import csv
import io
from src.repository.pergunta_repository import pergunta_repository
from src.repository.respostas_repository import resposta_repository
from src.repository.user_repository import user_repository

class DiagnosticoService:

    # Perguntas (Admin)
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
        # Busca o registro atual
        atual_res = await pergunta_repository.buscar_por_id(pergunta_id)
        if not atual_res.json():
            return {"status": 404, "erro": "Pergunta não encontrada"}

        atual = atual_res.json()[0]
        indice_atual = atual["indice"]
        ativa_atual = atual["ativa"]
        novo_indice = payload.get("indice", indice_atual)
        nova_ativa = payload.get("ativa", ativa_atual)

        # Caso 1: pergunta sendo INATIVADA
        if ativa_atual and not nova_ativa:
            # 1) Atualiza a pergunta, mantendo o índice dela (como você quer)
            response = await pergunta_repository.atualizar(pergunta_id, payload)
            if response.status_code not in (200, 204):
                response.raise_for_status()

            # 2) Recarrega todas as perguntas ativas
            ativas_res = await pergunta_repository.listar_ativas()
            if ativas_res.status_code not in (200, 206):
                ativas_res.raise_for_status()

            ativas = ativas_res.json()  # já vem ordenado por indice.asc

            # 3) Reatribui índices sequenciais apenas para as ativas
            novo_indice_seq = 1
            for p in ativas:
                if p["indice"] != novo_indice_seq:
                    await pergunta_repository.atualizar_indice(
                        p["id"], novo_indice_seq
                    )
                novo_indice_seq += 1

            return {"status": 200, "sucesso": "Pergunta atualizada"}

        # Caso 2: pergunta sendo REATIVADA 
        # Reinsere no índice correto e empurra as demais
        if not ativa_atual and nova_ativa:
            maiores_res = await pergunta_repository.listar_ativas_com_indice_gte(novo_indice)
            maiores = maiores_res.json() if maiores_res.status_code == 200 else []

            # Ordena decrescente para não colidir ao incrementar
            for registro in sorted(maiores, key=lambda x: x["indice"], reverse=True):
                if registro["id"] != pergunta_id:
                    await pergunta_repository.atualizar_indice(
                        registro["id"],
                        registro["indice"] + 1,
                    )

            response = await pergunta_repository.atualizar(pergunta_id, payload)
            if response.status_code not in (200, 204):
                response.raise_for_status()
            return {"status": 200, "sucesso": "Pergunta atualizada"}

        # Caso 3: pergunta permanece ativa, índice mudou
        if nova_ativa and novo_indice != indice_atual:
            conflito_res = await pergunta_repository.buscar_por_indice(novo_indice)
            conflito_data = conflito_res.json()

            if conflito_data:
                conflito_id = conflito_data[0]["id"]
                await pergunta_repository.atualizar_indice(conflito_id, indice_atual)

        # Atualiza o registro principal
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
    
    # Questionário (Todos os usuários)

    async def obter_sessao_atual(self, usuario_id: str):
        perguntas_res = await pergunta_repository.listar_ativas()
        if perguntas_res.status_code not in (200, 206):
            perguntas_res.raise_for_status()

        perguntas = perguntas_res.json()

        respostas_res = await resposta_repository.listar_por_usuario(usuario_id)
        respostas = respostas_res.json() if respostas_res.status_code == 200 else []

        respostas_map = {
            r["id_pergunta"]: {"id_resposta": r["id"], "pontuacao": r["pontuacao"]}
            for r in respostas
        }

        resultado = []
        for p in perguntas:
            resultado.append({
                "id_pergunta": p["id"],
                "indice": p["indice"],
                "ativa": p["ativa"],
                "eixo_esg": p["eixo_esg"],
                "tema": p["tema"],
                "exemplo": p.get("exemplo"),
                "pergunta": p["pergunta"],
                "resposta": respostas_map.get(p["id"]),
            })

        return {"status": 200, "data": resultado}

    async def salvar_respostas_lote(self, respostas: list, finalizado: bool = False):
        if not respostas:
            return {"status": 400, "erro": "Nenhuma resposta enviada"}

        usuario_id = respostas[0]["respondido_por"]

        # Upsert de todas as respostas
        response = await resposta_repository.upsert_lote(respostas)
        
        if response.status_code == 409:
            # logar o erro do Supabase
            print("DEBUG 409 Supabase:", response.text)
            return {
                "status": 409,
                "erro": (
                    f"Conflito ao salvar respostas: {response.text}"
                ),
            }
        
        if response.status_code not in (200, 201):
            response.raise_for_status()

        # Recalcula score do zero com base em TODAS as respostas do usuário
        todas_res = await resposta_repository.listar_por_usuario(usuario_id)
        todas = todas_res.json() if todas_res.status_code == 200 else []
        score_total = sum(r.get("pontuacao", 0) for r in todas)

        await user_repository.atualizar_score_esg(usuario_id, score_total)

        # Atualiza status
        novo_status = "Finalizada" if finalizado else "Em Andamento"
        await user_repository.atualizar_status_questionario(usuario_id, novo_status)

        return {"status": 200, "sucesso": "Respostas salvas"}

diagnostico_service = DiagnosticoService()