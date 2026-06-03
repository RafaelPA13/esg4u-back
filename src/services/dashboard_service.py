import csv
import io
from src.repository.dashboard_repository import dashboard_repository
from src.schemas.dashboard_schema import DashboardAdminSchema, RankingResponseSchema, RankingUsuarioSchema


class DashboardService:

    async def get_dashboard_admin(self):

        response = await dashboard_repository.get_dashboard_data()

        if response.status_code != 200:
            raise Exception("Erro ao consultar dashboard")

        data = response.json()

        if not data:
            return None

        return DashboardAdminSchema(**data[0])
    
    async def exportar_dashboard_csv(self):
        response = await dashboard_repository.get_dashboard_data()

        if response.status_code != 200:
            raise Exception("Erro ao consultar dashboard")

        data = response.json()

        if not data:
            return None

        dashboard = data[0]

        output = io.StringIO()

        fieldnames = [
            "total_usuarios",
            "score_esg_medio",
            "evidencias_anexadas",
            "validacoes_pendentes",
            "convites_enviados",
            "taxa_conversao_convites",
            "bugs_reportados",
        ]

        writer = csv.DictWriter(output, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerow(dashboard)

        output.seek(0)

        return output.getvalue()
    
    async def get_ranking(self, user_id: str):

        top_response = await dashboard_repository.get_top_10()

        if top_response.status_code != 200:
            raise Exception("Erro ao buscar ranking")

        user_response = await dashboard_repository.get_user_position(user_id)

        if user_response.status_code != 200:
            raise Exception("Erro ao buscar posição do usuário")

        top_10 = [
            RankingUsuarioSchema(**item)
            for item in top_response.json()
        ]

        minha_posicao = None

        user_data = user_response.json()

        if user_data:
            minha_posicao = RankingUsuarioSchema(
                **user_data[0]
            )

        return RankingResponseSchema(
            top_10=top_10,
            minha_posicao=minha_posicao
        )


dashboard_service = DashboardService()