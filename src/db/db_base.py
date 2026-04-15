# src/db/db_base.py
import httpx
from typing import List, Dict, Any, Optional
from src.core.config import settings

class SupabaseClient:
    def __init__(self, table_name: str, use_service_role: bool = False):
        self.base_url = f"{settings.SUPABASE_URL}/rest/v1/{table_name}"
        self.headers = {
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY if use_service_role else settings.SUPABASE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}" if use_service_role else f"Bearer {settings.SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation" # Garante que o retorno seja o objeto inserido/atualizado
        }
        self.client = httpx.AsyncClient() # Cliente assíncrono para FastAPI

    async def _make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """
        Função interna para fazer requisições HTTP para o Supabase.
        """
        try:
            response = await self.client.request(method, url, headers=self.headers, **kwargs)
            response.raise_for_status() # Levanta exceção para status de erro HTTP
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Erro HTTP ao acessar Supabase: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            print(f"Erro de requisição ao acessar Supabase: {e}")
            raise

    async def insert(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Insere um novo registro na tabela.
        """
        result = await self._make_request("POST", self.base_url, json=data)
        return result[0] if result else None # Supabase retorna uma lista de objetos inseridos

    async def select_all(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Seleciona todos os registros da tabela, opcionalmente com filtros.
        Ex: filters={"email": "teste@example.com", "status": "ativo"}
        """
        query_params = []
        if filters:
            for key, value in filters.items():
                query_params.append(f"{key}=eq.{value}") # Ex: email=eq.teste@example.com

        url = self.base_url
        if query_params:
            url += "?" + "&".join(query_params)

        return await self._make_request("GET", url)

    async def select_by_id(self, id_value: Any) -> Optional[Dict[str, Any]]:
        """
        Seleciona um registro pelo ID.
        """
        url = f"{self.base_url}?id=eq.{id_value}"
        result = await self._make_request("GET", url)
        return result[0] if result else None

    async def update(self, id_value: Any, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Atualiza um registro pelo ID.
        """
        url = f"{self.base_url}?id=eq.{id_value}"
        result = await self._make_request("PATCH", url, json=data)
        return result[0] if result else None

    async def delete(self, id_value: Any) -> Optional[Dict[str, Any]]:
        """
        Deleta um registro pelo ID.
        """
        url = f"{self.base_url}?id=eq.{id_value}"
        result = await self._make_request("DELETE", url)
        return result[0] if result else None