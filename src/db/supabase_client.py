import httpx
from src.core.config import settings

class SupabaseClient:

    def __init__(self):
        self.base_url = settings.SUPABASE_URL
        self.service_key = settings.SUPABASE_SERVICE_ROLE_KEY
        self.public_key = settings.SUPABASE_KEY

    async def post(self, path: str, data: dict, use_service_key: bool = True):
        headers = {
            "Content-Type": "application/json",
            "apikey": self.service_key if use_service_key else self.public_key,
            "Authorization": f"Bearer {self.service_key if use_service_key else self.public_key}"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}{path}",
                json=data,
                headers=headers
            )

        return response

supabase = SupabaseClient()