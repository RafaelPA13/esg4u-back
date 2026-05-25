import asyncio

from src.repository.validacoes_repository import validacoes_repository
from src.repository.pergunta_repository import pergunta_repository
from src.repository.respostas_repository import resposta_repository
from src.repository.evidencias_repository import evidencias_repository
from src.repository.user_repository import user_repository
from src.services.email_service import email_service


class ValidacoesService:

    async def pedir_validacao(self, payload: dict, usuario_email: str):
        """
        POST /validacoes/pedir_validacao
        payload: { id_resposta, pedido_por (email), avaliador_email (email), avaliador_nome (opcional, só para e-mail) }
        """
        id_resposta = payload.get("id_resposta")
        pedido_por = payload.get("pedido_por")     # email
        avaliador = payload.get("avaliador_email") # email

        if not id_resposta or not pedido_por or not avaliador:
            return {"status": 400, "erro": "Campos obrigatórios não preenchidos"}

        # Garante que o usuário autenticado é o mesmo do pedido_por
        if str(usuario_email) != str(pedido_por):
            return {"status": 403, "erro": "Você só pode pedir validação para suas próprias respostas"}

        # RN: avaliador != pedido_por
        if pedido_por == avaliador:
            return {"status": 403, "erro": "O avaliador não pode ser a mesma pessoa que pediu a validação"}

        # Verificar se já existe validação para esta resposta
        res_existente = await validacoes_repository.listar_validacoes_por_email_e_resposta(pedido_por, id_resposta)
        if res_existente.status_code == 200 and res_existente.json():
            return {"status": 409, "erro": "Já existe uma solicitação de validação para esta resposta."}

        # Buscar pontuação base da resposta
        res_resposta = await resposta_repository.buscar_por_id(id_resposta)
        if res_resposta.status_code != 200 or not res_resposta.json():
            return {"status": 400, "erro": "Resposta não encontrada"}

        pontuacao_base = res_resposta.json()[0]["pontuacao"]

        # Montar payload final — validado sempre "pendente" na criação
        validacao_payload = {
            "id_resposta": id_resposta,
            "pedido_por": pedido_por,
            "avaliador": avaliador,
            "validado": "pendente",
            "pontuacao": pontuacao_base,
        }

        resp_criar = await validacoes_repository.criar_validacao(validacao_payload)
        if resp_criar.status_code not in (200, 201):
            return {"status": resp_criar.status_code, "erro": resp_criar.text}

        # Enviar e-mail de notificação ao avaliador (RN1)
        pedido_por_res = await user_repository.find_by_email(pedido_por)
        avaliador_res = await user_repository.find_by_email(avaliador)

        pedido_por_user = pedido_por_res.json()[0] if (pedido_por_res.status_code == 200 and pedido_por_res.json()) else None
        avaliador_user = avaliador_res.json()[0] if (avaliador_res.status_code == 200 and avaliador_res.json()) else None

        if pedido_por_user:
            # Nome do avaliador: usa o cadastrado ou o nome enviado no payload
            nome_avaliador = (
                avaliador_user["nome"] if avaliador_user 
                else payload.get("avaliador_nome", avaliador)  # fallback para o email
            )
            # Email do avaliador: usa o cadastrado ou o email enviado diretamente
            email_avaliador = avaliador_user["email"] if avaliador_user else avaliador

            template_data = await user_repository.get_template_by_name("template_email_solicitacao_validacao")
            if template_data and len(template_data) > 0:
                template = template_data[0].get("conteudo", "")
                html = (
                    template
                    .replace("{{NOME_AVALIADOR}}", nome_avaliador)
                    .replace("{{NOME_SOLICITANTE}}", pedido_por_user["nome"])
                )
                asyncio.create_task(
                    asyncio.to_thread(
                        email_service.send_email,
                        email_avaliador,
                        "Solicitação de validação ESG4U",
                        html,
                    )
                )
            else:
                print("Aviso: Template 'template_email_solicitacao_validacao' não encontrado.")
        else:
            print("Aviso: Usuário solicitante não encontrado para enviar e-mail.")

        return {"status": 201, "sucesso": "Validação solicitada"}

    async def validar(self, validacao_id: int, payload: dict):
        """
        PUT /validacoes/validar/{validacao_id}
        payload: { validado: "validado" | "rejeitado" }
        """
        # Buscar validação
        res_val = await validacoes_repository.buscar_por_id(validacao_id)
        if res_val.status_code != 200 or not res_val.json():
            return {"status": 400, "erro": "Validação não encontrada"}

        validacao = res_val.json()[0]
        id_resposta = validacao["id_resposta"]
        pedido_por_email = validacao["pedido_por"]   # email
        avaliador_email = validacao["avaliador"]     # email
        decisao = payload.get("validado")
        pontuacao_base = validacao["pontuacao"]

        # RN1: calcular pontuação com multiplicador
        res_evid = await evidencias_repository.buscar_por_resposta(id_resposta)
        has_evidencia = res_evid and res_evid.status_code == 200 and res_evid.json()

        if decisao == "validado":
            fator = 1.7 if has_evidencia else 1.2
            pontuacao_final = round(pontuacao_base * fator, 2)
        else:
            # Rejeitado: mantém pontuação base
            pontuacao_final = pontuacao_base

        # Atualizar validação
        resp_update = await validacoes_repository.atualizar_validacao(
            validacao_id,
            {"validado": decisao, "pontuacao": pontuacao_final},
        )
        if resp_update.status_code not in (200, 204):
            return {"status": resp_update.status_code, "erro": resp_update.text}

        # Buscar usuários pelo email para obter o ID (necessário para atualizar score/reputação)
        res_pedido_por = await user_repository.find_by_email(pedido_por_email)
        res_avaliador = await user_repository.find_by_email(avaliador_email)

        if not (res_pedido_por.status_code == 200 and res_pedido_por.json()):
            return {"status": 400, "erro": "Usuário solicitante não encontrado"}
        if not (res_avaliador.status_code == 200 and res_avaliador.json()):
            return {"status": 400, "erro": "Usuário avaliador não encontrado"}

        pedido_por_user = res_pedido_por.json()[0]
        avaliador_user = res_avaliador.json()[0]

        # RN1: Recalcular score_esg do solicitante (usando email como chave nas validações)
        await self._recalcular_score_esg_usuario(
            usuario_id=str(pedido_por_user["id"]),
            pedido_por_email=pedido_por_email,
        )

        # RN2: Reputação do avaliador: sempre +10
        await self._atualizar_reputacao(str(avaliador_user["id"]), delta=10)

        # RN2: Reputação do solicitante: +10 se validado, -10 se rejeitado
        delta_solicitante = 10 if decisao == "validado" else -10
        await self._atualizar_reputacao(str(pedido_por_user["id"]), delta=delta_solicitante)

        return {"status": 200, "sucesso": "Resposta avaliada"}

    async def _recalcular_score_esg_usuario(self, usuario_id: str, pedido_por_email: str):
        res_respostas = await resposta_repository.listar_por_usuario(usuario_id)
        respostas_usuario = res_respostas.json() if res_respostas.status_code == 200 else []

        if not respostas_usuario:
            await user_repository.atualizar_score_esg(usuario_id, 0.0)
            return

        ids_respostas = [r["id"] for r in respostas_usuario]

        # Evidências
        mapa_evidencias = {}
        res_evids = await evidencias_repository.listar_por_respostas(ids_respostas)
        if res_evids and res_evids.status_code == 200:
            for e in res_evids.json():
                mapa_evidencias[e["id_resposta"]] = e

        # Todas as validações resolvidas (validado OU rejeitado) — exclui apenas pendente
        mapa_validacoes = {}
        res_vals = await validacoes_repository.listar_resolvidas_por_respostas(pedido_por_email, ids_respostas)
        if res_vals.status_code == 200 and res_vals.json():
            for v in res_vals.json():
                mapa_validacoes[v["id_resposta"]] = v

        score_total = 0.0
        for r in respostas_usuario:
            id_resp = r["id"]
            val = mapa_validacoes.get(id_resp)

            if val and val["validado"] == "validado":
                # Aprovada: usa pontuação com multiplicador já salvo na validação
                score_total += val["pontuacao"]
            elif val and val["validado"] == "rejeitado":
                # Rejeitada: usa pontuação base, ignora evidência
                score_total += r["pontuacao"]
            elif id_resp in mapa_evidencias:
                # Sem validação resolvida mas tem evidência: usa pontuação da evidência
                score_total += mapa_evidencias[id_resp]["pontuacao"]
            else:
                # Sem validação e sem evidência: pontuação base
                score_total += r["pontuacao"]

        await user_repository.atualizar_score_esg(usuario_id, round(score_total, 2))

    async def _atualizar_reputacao(self, usuario_id: str, delta: int):
        """Incrementa ou decrementa a reputação de um usuário."""
        res_user = await user_repository.find_by_id(usuario_id)
        if res_user.status_code != 200 or not res_user.json():
            print(f"Aviso: Usuário {usuario_id} não encontrado para atualizar reputação.")
            return

        reputacao_atual = res_user.json()[0].get("reputacao") or 0
        resp_update = await user_repository.update_user(
            usuario_id,
            {"reputacao": reputacao_atual + delta},
        )
        if resp_update.status_code not in (200, 204):
            print(f"Erro ao atualizar reputação do usuário {usuario_id}: {resp_update.text}")

    async def listar_por_avaliador(self, avaliador_email: str):
        """
        GET /validacoes/{avaliador_email}
        Busca validações atribuídas ao avaliador e enriquece com
        dados da resposta, pergunta e evidência do solicitante.
        """
        # RN6: Buscar validações onde este e-mail é o avaliador
        res_vals = await validacoes_repository.listar_por_avaliador_email(avaliador_email)
        if res_vals.status_code != 200 or not res_vals.json():
            return {"status": 204, "sucesso": "Nenhum registro encontrado"}

        validacoes = res_vals.json()
        resultado = []

        for v in validacoes:
            id_resposta = v["id_resposta"]

            # Buscar resposta (pertence ao solicitante)
            res_resposta = await resposta_repository.buscar_por_id(id_resposta)
            if res_resposta.status_code != 200 or not res_resposta.json():
                continue
            resposta = res_resposta.json()[0]

            # Buscar pergunta a partir do id_pergunta da resposta
            res_pergunta = await pergunta_repository.buscar_por_id(resposta["id_pergunta"])
            if res_pergunta.status_code != 200 or not res_pergunta.json():
                continue
            pergunta = res_pergunta.json()[0]

            # RN5: Buscar evidência atrelada à resposta
            evid = None
            res_evid = await evidencias_repository.buscar_por_resposta(id_resposta)
            if res_evid and res_evid.status_code == 200 and res_evid.json():
                e = res_evid.json()[0]
                evid = {
                    "id_evidencia": e["id"],
                    "evidencia": e["evidencia"],
                    "pontuacao": e["pontuacao"],
                    "dt_postagem": e["created_at"],
                }

            resultado.append({
                "id_pergunta": pergunta["id"],
                "pergunta": pergunta["pergunta"],
                "eixo_esg": pergunta["eixo_esg"],
                "resposta": {
                    "id_resposta": id_resposta,
                    "pontuacao": resposta["pontuacao"],
                },
                "evidencia": evid,
                "validacao": {
                    "id_validacao": v["id"],
                    "validado": v["validado"],
                    "pedido_por": v["pedido_por"],
                    "pontuacao": v["pontuacao"],
                },
            })

        if not resultado:
            return {"status": 204, "sucesso": "Nenhum registro encontrado"}

        return {"status": 200, "data": resultado}

    async def listar_minhas_validacoes(self, pedido_por_email: str):
        """
        GET /validacoes/minhas_validacoes/{pedido_por_email}
        Retorna todas as perguntas respondidas pelo usuário,
        com evidência e validação (null se não houver).
        """
        # RN2: Buscar usuário pelo email
        res_user = await user_repository.find_by_email(pedido_por_email)
        if res_user.status_code != 200 or not res_user.json():
            return {"status": 400, "erro": "Usuário não encontrado"}
        usuario = res_user.json()[0]
        usuario_id = str(usuario["id"])

        # RN3: Listar perguntas ativas
        res_perguntas = await pergunta_repository.listar_ativas()
        if res_perguntas.status_code != 200:
            return {"status": res_perguntas.status_code, "erro": res_perguntas.text}
        perguntas = res_perguntas.json() or []

        # RN4: Listar respostas do usuário
        res_respostas = await resposta_repository.listar_por_usuario(usuario_id)
        if res_respostas.status_code != 200:
            return {"status": res_respostas.status_code, "erro": res_respostas.text}
        respostas = res_respostas.json() or []

        mapa_respostas = {r["id_pergunta"]: r for r in respostas}
        ids_respostas = [r["id"] for r in respostas]

        # RN5: Buscar evidências
        mapa_evidencias = {}
        if ids_respostas:
            res_evids = await evidencias_repository.listar_por_respostas(ids_respostas)
            if res_evids and res_evids.status_code == 200:
                for e in res_evids.json():
                    mapa_evidencias[e["id_resposta"]] = e

        # RN6: Buscar validações onde este usuário é o solicitante
        res_vals = await validacoes_repository.listar_por_pedido_por_email(pedido_por_email)
        mapa_validacoes = {}
        if res_vals.status_code == 200 and res_vals.json():
            for v in res_vals.json():
                mapa_validacoes[v["id_resposta"]] = v

        resultado = []
        for perg in perguntas:
            resposta = mapa_respostas.get(perg["id"])
            if not resposta:
                continue  # pergunta sem resposta do usuário — ignorar

            id_resp = resposta["id"]
            evid_raw = mapa_evidencias.get(id_resp)
            val_raw = mapa_validacoes.get(id_resp)

            evid = None
            if evid_raw:
                evid = {
                    "id_evidencia": evid_raw["id"],
                    "evidencia": evid_raw["evidencia"],
                    "pontuacao": evid_raw["pontuacao"],
                    "dt_postagem": evid_raw["created_at"],
                }

            # validacao é null se não houver solicitação ainda
            validacao = None
            if val_raw:
                validacao = {
                    "id_validacao": val_raw["id"],
                    "validado": val_raw["validado"],
                    "avaliador": val_raw["avaliador"],
                    "pontuacao": val_raw["pontuacao"],
                }

            resultado.append({
                "id_pergunta": perg["id"],
                "pergunta": perg["pergunta"],
                "eixo_esg": perg["eixo_esg"],
                "resposta": {
                    "id_resposta": id_resp,
                    "pontuacao": resposta["pontuacao"],
                },
                "evidencia": evid,
                "validacao": validacao,  # None se não houver validação
            })

        if not resultado:
            return {"status": 204, "sucesso": "Nenhum registro encontrado"}

        return {"status": 200, "data": resultado}


validacoes_service = ValidacoesService()