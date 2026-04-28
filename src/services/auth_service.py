import uuid
import random
import asyncio
import httpx
import re
import csv
import io
from math import ceil
from datetime import datetime, timedelta, timezone
from uuid import UUID

from src.core.config import settings
from src.repository.user_repository import user_repository
from src.services.email_service import email_service
from src.db.supabase_client import supabase
from src.schemas.auth_schema import UserResponseSchema, UserUpdateSchema


class AuthService:
    async def create_auth_user(self, email: str, password: str):
        response = await supabase.post(
            "/auth/v1/admin/users",
            {"email": email, "password": password, "email_confirm": False},
        )
        return response

    def gerar_codigo(self) -> str:
        return str(random.randint(100000, 999999))

    async def cadastrar(self, data):
        nome = data.nome
        email = data.email
        senha = data.senha
        confirmar = data.confirmar_senha

        # Validação básica
        if not nome or not email or not senha:
            raise Exception("Campos obrigatórios não preenchidos")

        if senha != confirmar:
            raise Exception("As senhas precisam ser idênticas")

        # Verificar se já existe no banco
        existente = await user_repository.find_by_email(email)
        if existente.status_code == 200 and len(existente.json()) > 0:
            raise Exception("E-mail já cadastrado")

        # Criar usuário no Supabase Auth
        auth_response = await self.create_auth_user(email, senha)

        if auth_response.status_code >= 400:
            raise Exception("Erro ao criar usuário")

        user_data = auth_response.json()
        user_id = user_data.get("id")

        if not user_id:
            raise Exception("Erro ao obter ID do usuário")

        # Criar na tabela usuarios
        create_user_response = await user_repository.create_user(
            {"id": user_id, "nome": nome, "email": email}
        )

        if create_user_response.status_code >= 400:
            raise Exception("Erro ao salvar usuário")

        # Gerar código de verificação
        codigo = self.gerar_codigo()

        expires_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()

        # Salvar token
        await user_repository.create_token(
            {
                "user_id": user_id,
                "tipo": "email_confirmacao",
                "codigo": codigo,
                "expires_at": expires_at,
            }
        )

        # Buscar template de e-mail
        template_data = await user_repository.get_template()

        if not template_data or len(template_data) == 0:
            raise Exception("Template de email não encontrado")

        template = template_data[0].get("conteudo", "")

        # Substituir código no template
        html = template.replace("{{CODIGO_DE_CONFIRMACAO}}", codigo)

        # Envio de e-mail (não bloqueante)
        asyncio.create_task(
            asyncio.to_thread(
                email_service.send_email, email, "Código de verificação", html
            )
        )

        return {"sucesso": "Usuário criado com sucesso"}

    async def validar_codigo(self, codigo: str):
        if not codigo:
            raise Exception("Código inválido")

        response = await user_repository.get_token_by_codigo(codigo)

        if response.status_code != 200 or len(response.json()) == 0:
            raise Exception("Código inválido")

        token = response.json()[0]

        user_id = token["user_id"]
        expires_at = token["expires_at"]
        token_id = token["id"]

        # Expiração
        if datetime.now(timezone.utc) > datetime.fromisoformat(expires_at):
            await user_repository.delete_user(user_id)

            await supabase.post(
                f"/auth/v1/admin/users/{user_id}", {"ban_duration": "876000h"}
            )

            raise Exception("Código expirado")

        # Marcar como usado
        await user_repository.mark_token_used(token_id)

        # Confirmar email
        async def update_auth_user(user_id: str, data: dict):
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{settings.SUPABASE_URL}/auth/v1/admin/users/{user_id}",
                    headers={
                        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                        "Content-Type": "application/json",
                    },
                    json=data,
                )
            return response

        await update_auth_user(user_id, {"email_confirm": True})

        return {"sucesso": "Código validado com sucesso"}

    async def reenviar_codigo(self, email: str):
        if not email:
            raise Exception("Email obrigatório")

        user_res = await user_repository.find_by_email(email)

        if user_res.status_code != 200 or len(user_res.json()) == 0:
            raise Exception("Usuário não encontrado")

        user = user_res.json()[0]
        user_id = user["id"]

        # Buscar token existente
        token_res = await user_repository.get_token_by_user(
            user_id, "email_confirmacao"
        )

        novo_codigo = self.gerar_codigo()
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()

        if token_res.status_code == 200 and len(token_res.json()) > 0:
            token = token_res.json()[0]

            await user_repository.update_token(token["id"], novo_codigo, expires_at)
        else:
            await user_repository.create_token(
                {
                    "user_id": user_id,
                    "tipo": "email_confirmacao",
                    "codigo": novo_codigo,
                    "expires_at": expires_at,
                }
            )

        # Template
        template_data = await user_repository.get_template()

        template = template_data[0].get("conteudo", "")
        html = template.replace("{{CODIGO_DE_CONFIRMACAO}}", novo_codigo)

        asyncio.create_task(
            asyncio.to_thread(
                email_service.send_email, email, "Novo código de verificação", html
            )
        )

        return {"sucesso": "E-mail reenviado"}

    async def solicitar_reset(self, email: str):
        if not email:
            raise Exception("Email obrigatório")

        user_res = await user_repository.find_by_email(email)

        # NÃO revelar se existe
        if user_res.status_code != 200 or len(user_res.json()) == 0:
            return {"sucesso": "E-mail Enviado"}

        user = user_res.json()[0]
        user_id = user["id"]

        # Gerar token (UUID)
        token = str(uuid.uuid4())

        expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

        # Salvar token
        await user_repository.create_token(
            {
                "user_id": user_id,
                "tipo": "reset_senha",
                "codigo": token,
                "expires_at": expires_at,
            }
        )

        # Buscar template
        async with httpx.AsyncClient() as client:
            template_res = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/parametros",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                },
                params={"id": "eq.template_email_reset_senha"},
            )

        template_data = template_res.json()

        template = template_data[0]["conteudo"]

        link = f"http://localhost:5173/autenticacao/redefinir-senha?token={token}"  # TODO: Alterar para o link da hospedagem

        html = template.replace("{{LINK_RESET}}", link)

        asyncio.create_task(
            asyncio.to_thread(
                email_service.send_email, email, "Redefinição de senha", html
            )
        )

        return {"sucesso": "E-mail enviado"}

    async def redefinir_senha(self, token: str, senha: str, confirmar: str):
        if not token or not senha:
            raise Exception("Dados inválidos")

        if senha != confirmar:
            raise Exception("As senhas devem ser idênticas")

        if len(senha) < 8:
            raise Exception("Senha deve ter no mínimo 8 caracteres")

        if not re.search(r"[A-Z]", senha):
            raise Exception("Senha deve ter letra maiúscula")

        if not re.search(r"[a-z]", senha):
            raise Exception("Senha deve ter letra minúscula")

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", senha):
            raise Exception("Senha deve ter caractere especial")

        # Buscar token
        token_res = await user_repository.get_token_by_valor(token, "reset_senha")

        if token_res.status_code != 200 or len(token_res.json()) == 0:
            raise Exception("Token inválido")

        token_data = token_res.json()[0]

        user_id = token_data["user_id"]
        expires_at = token_data["expires_at"]
        token_id = token_data["id"]

        # Expiração
        if datetime.now(timezone.utc) > datetime.fromisoformat(expires_at):
            await user_repository.mark_token_used(token_id)
            raise Exception("Token expirado")

        # Atualizar senha no Supabase
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{settings.SUPABASE_URL}/auth/v1/admin/users/{user_id}",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                    "Content-Type": "application/json",
                },
                json={"password": senha},
            )

        if response.status_code >= 400:
            raise Exception("Erro ao redefinir senha")

        # Marcar token como usado
        await user_repository.mark_token_used(token_id)

        return {"sucesso": "Senha redefinida com sucesso"}

    async def login(self, email: str, senha: str):
        if not email or not senha:
            raise Exception("Credenciais inválidas")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=password",
                headers={
                    "apikey": settings.SUPABASE_KEY,
                    "Content-Type": "application/json",
                },
                json={"email": email, "password": senha},
            )

        # Erro de autenticação
        if response.status_code != 200:
            raise Exception("Credenciais inválidas")

        data = response.json()

        # Garantir que tem token
        access_token = data.get("access_token")

        if not access_token:
            raise Exception("Nenhum token encontrado")

        # Retorno padronizado
        return {"token": access_token}

    async def me(self, authorization: str):
        # authorization vem como "Bearer <token>"
        if not authorization.startswith("Bearer "):
            raise Exception("Token inválido")

        access_token = authorization.replace("Bearer ", "").strip()

        # 1. Pegar usuário atual no Supabase Auth
        async with httpx.AsyncClient() as client:
            auth_res = await client.get(
                f"{settings.SUPABASE_URL}/auth/v1/user",
                headers={
                    "apikey": settings.SUPABASE_KEY,
                    "Authorization": f"Bearer {access_token}",
                },
            )

        if auth_res.status_code != 200:
            raise Exception("Não autenticado")

        auth_user = auth_res.json()
        user_id = auth_user.get("id")
        email = auth_user.get("email")

        if not user_id:
            raise Exception("Usuário inválido")

        # 2. Buscar na tabela usuarios
        user_res = await user_repository.find_by_id(user_id)

        if user_res.status_code != 200 or len(user_res.json()) == 0:
            # fallback: se não achar na tabela, ainda assim retorna o básico
            return {
                "id": user_id,
                "email": email,
                "nome": auth_user.get("user_metadata", {}).get("nome"),
                "admin": False,
            }

        usuario = user_res.json()[0]

        return {
            "id": usuario["id"],
            "nome": usuario.get("nome"),
            "email": usuario.get("email") or email,
            "admin": usuario.get("admin", False),
        }

    async def get_all_users(self, page: int, per_page: int, filters: dict):
        """
        Busca usuários com paginação e filtros.
        """

        # 1) Buscar a página
        list_res = await user_repository.list_users_paginated(page, per_page, filters)

        if list_res.status_code not in (200, 206):  # 206 = Partial Content
            list_res.raise_for_status()

        users_data = list_res.json()  # pode ser [] ou lista

        # 2) Contar total (usando mesma filtragem)
        count_res = await user_repository.count_users(filters)

        if count_res.status_code not in (200, 206):
            count_res.raise_for_status()

        # Supabase devolve o total no header "Content-Range": "0-11/12"
        content_range = count_res.headers.get("Content-Range", "0-0/0")
        total_str = content_range.split("/")[-1]  # depois da barra
        try:
            total_records = int(total_str)
        except ValueError:
            total_records = 0

        # Se não há nenhum registro, retorna 204 conforme especificação
        if total_records == 0:
            return None  # vamos tratar isso no router com 204

        # 3) Calcular paginação
        total_pages = ceil(total_records / per_page) if per_page > 0 else 0

        prox_page = page < total_pages
        prev_page = page > 1

        # 4) Mapear para schema
        users = [UserResponseSchema(**u) for u in users_data]

        return {
            "users": users,
            "registros": total_records,
            "pages": total_pages,
            "page": page,
            "per_page": per_page,
            "prox_page": prox_page,
            "prev_page": prev_page,
        }

    async def get_user_by_id(self, user_id: UUID):
        """
        Busca um usuário pelo ID.
        """
        response = await user_repository.find_by_id(str(user_id))
        if response.status_code == 200 and len(response.json()) > 0:
            return UserResponseSchema(**response.json()[0])
        return "Nenhum registro encontrado"

    async def update_user_data(self, user_id: UUID, user_data: UserUpdateSchema):
        """
        Atualiza os dados de um usuário.
        """
        update_dict = user_data.model_dump(
            exclude_unset=True
        )  # Pega apenas os campos que foram passados

        if not update_dict:
            raise Exception("Nenhum dado para atualizar.")

        # Se o email for atualizado, atualiza no Supabase Auth também
        if "email" in update_dict and update_dict["email"]:
            auth_update_response = await user_repository.update_supabase_auth_email(
                str(user_id), update_dict["email"]
            )
            if auth_update_response.status_code >= 400:
                raise Exception(
                    f"Erro ao atualizar email no Supabase Auth: {auth_update_response.text}"
                )

        # Atualiza na tabela 'usuarios'
        db_update_response = await user_repository.update_user(
            str(user_id), update_dict
        )
        if db_update_response.status_code >= 400:
            raise Exception(
                f"Erro ao atualizar usuário no banco de dados: {db_update_response.text}"
            )

        return {"message": "Usuário Atualizado."}

    async def delete_user_by_id(self, user_id: UUID):
        """
        Deleta um usuário do Supabase Auth e da tabela 'usuarios'.
        """
        # Primeiro, deleta do Supabase Auth
        auth_delete_response = await user_repository.delete_supabase_auth_user(
            str(user_id)
        )
        if auth_delete_response.status_code >= 400:
            raise Exception(
                f"Erro ao deletar usuário do Supabase Auth: {auth_delete_response.text}"
            )

        # Em seguida, deleta da tabela 'usuarios'
        db_delete_response = await user_repository.delete_user_from_db(str(user_id))
        if db_delete_response.status_code >= 400:
            raise Exception(
                f"Erro ao deletar usuário do banco de dados: {db_delete_response.text}"
            )

        return {"message": "Usuário Excluído."}

    async def exportar_usuarios_csv(self):
        """
        Busca todos os usuários e gera um CSV em memória.
        """
        response = await user_repository.list_all_users_for_export()

        if response.status_code not in (200, 206):
            response.raise_for_status()

        users_data = response.json()

        if not users_data:
            return None

        output = io.StringIO()
        fieldnames = ["id", "nome", "email", "score_esg", "trust_score", "reputacao", "admin"]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(users_data)
        output.seek(0)

        return output.getvalue()

auth_service = AuthService()
