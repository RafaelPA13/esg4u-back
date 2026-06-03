import io
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse
from src.services.auth_service import auth_service
from src.services.dashboard_service import dashboard_service
from src.schemas.dashboard_schema import DashboardAdminSchema, RankingResponseSchema


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

# Dependência para verificar se o usuário é admin
async def get_current_admin_user(authorization: str = Header(...)):
    user_info = await auth_service.me(authorization)
    if not user_info or not user_info.get("admin"):
        raise HTTPException(status_code=401, detail="Usuário não autorizado")
    return user_info

# Dependência para obter o usuário autenticado (não necessariamente admin)
async def get_current_user(authorization: str = Header(...)):
    user_info = await auth_service.me(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    return user_info

@router.get("/visao-geral", response_model=DashboardAdminSchema)
async def get_dashboard_endpoint(
    admin_user: dict = Depends(get_current_admin_user)
):

    result = await dashboard_service.get_dashboard_admin()

    if result is None:
        raise HTTPException(
            status_code=204,
            detail="Nenhum dado encontrado"
        )

    return result


@router.get("/exportar-csv")
async def exportar_dashboard_csv_endpoint(
    admin_user: dict = Depends(get_current_admin_user),
):
    csv_content = await dashboard_service.exportar_dashboard_csv()

    if csv_content is None:
        raise HTTPException(
            status_code=204,
            detail="Nenhum registro encontrado."
        )

    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=dashboard_admin.csv"
        }
    )
    
    
@router.get("/ranking", response_model=RankingResponseSchema)
async def get_ranking(
    current_user: dict = Depends(get_current_user)
):

    return await dashboard_service.get_ranking(
        current_user["id"]
    )