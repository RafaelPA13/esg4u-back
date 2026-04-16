import uuid
import random
import asyncio
import httpx
import re
from datetime import datetime, timedelta, timezone

from src.core.config import settings
from src.repository.user_repository import user_repository
from src.services.email_service import email_service
from src.db.supabase_client import supabase


class AuthService:

    async def create_auth_user(self, email: str, password: str):
        response = await supabase.post(
            "/auth/v1/admin/users",
            {
                "email": email,
                "password": password,
                "email_confirm": False
            }
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
        create_user_response = await user_repository.create_user({
            "id": user_id,
            "nome": nome,
            "email": email
        })

        if create_user_response.status_code >= 400:
            raise Exception("Erro ao salvar usuário")

        # Gerar código de verificação
        codigo = self.gerar_codigo()

        expires_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()

        # Salvar token
        await user_repository.create_token({
            "user_id": user_id,
            "tipo": "email_confirmacao",
            "codigo": codigo,
            "expires_at": expires_at
        })

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
                email_service.send_email,
                email,
                "Código de verificação",
                html
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
                f"/auth/v1/admin/users/{user_id}",
                {"ban_duration": "876000h"}
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
                        "Content-Type": "application/json"
                    },
                    json=data
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
            user_id,
            "email_confirmacao"
        )

        novo_codigo = self.gerar_codigo()
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()

        if token_res.status_code == 200 and len(token_res.json()) > 0:
            token = token_res.json()[0]

            await user_repository.update_token(
                token["id"],
                novo_codigo,
                expires_at
            )
        else:
            await user_repository.create_token({
                "user_id": user_id,
                "tipo": "email_confirmacao",
                "codigo": novo_codigo,
                "expires_at": expires_at
            })

        # Template
        template_data = await user_repository.get_template()

        template = template_data[0].get("conteudo", "")
        html = template.replace("{{CODIGO_DE_CONFIRMACAO}}", novo_codigo)

        asyncio.create_task(
            asyncio.to_thread(
                email_service.send_email,
                email,
                "Novo código de verificação",
                html
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
        await user_repository.create_token({
            "user_id": user_id,
            "tipo": "reset_senha",
            "codigo": token,
            "expires_at": expires_at
        })

        # Buscar template
        async with httpx.AsyncClient() as client:
            template_res = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/parametros",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                },
                params={"id": "eq.template_email_reset_senha"}
            )

        template_data = template_res.json()

        template = template_data[0]["conteudo"]

        link = f"http://localhost:5173/reset-password?token={token}" #TODO: Alterar para o link da hospedagem

        html = template.replace("{{LINK_RESET}}", link)

        asyncio.create_task(
            asyncio.to_thread(
                email_service.send_email,
                email,
                "Redefinição de senha",
                html
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
        token_res = await user_repository.get_token_by_valor(
            token,
            "reset_senha"
        )

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
                    "Content-Type": "application/json"
                },
                json={"password": senha}
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
                    "Content-Type": "application/json"
                },
                json={
                    "email": email,
                    "password": senha
                }
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
        return {
            "token": access_token
        }

auth_service = AuthService()