import httpx

from src.core.config import settings


class DashboardRepository:

    async def get_dashboard_data(self):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/vw_dashboard_admin",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                    "Accept": "application/json",
                },
            )

        return response
    
    async def get_top_10(self):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/vw_ranking_esg",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                },
                params={
                    "order": "posicao.asc",
                    "limit": 10,
                }
            )

        return response

    async def get_user_position(self, user_id: str):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/vw_ranking_esg",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                },
                params={
                    "id": f"eq.{user_id}"
                }
            )

        return response


dashboard_repository = DashboardRepository()