import io
from fastapi import APIRouter, HTTPException, Header, Depends, Query
from fastapi.responses import StreamingResponse
from src.services.auth_service import auth_service
from src.services.convites_service import convites_service
from src.schemas.convites_schema import EnviarConviteSchema
from typing import Optional, Dict


router = APIRouter(prefix="/convites", tags=["Convites"])


async def get_current_user(authorization: str = Header(...)):
    user_info = await auth_service.me(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="Credenciais expiradas, logue novamente")
    return user_info

async def get_current_admin_user(current_user: Dict = Depends(get_current_user)):
    if not current_user.get("admin"):
        raise HTTPException(status_code=403, detail="Acesso negado: Somente administradores podem acessar este recurso")
    return current_user


# POST: /convites/enviar_convite
@router.post("/enviar_convite", status_code=201)
async def enviar_convite(
    data: EnviarConviteSchema,
    current_user: Dict = Depends(get_current_user),
):
    remetente_id = current_user["id"]
    remetente_nome = current_user["nome"] # Assumindo que o nome do usuário está no token/user_info

    result = await convites_service.enviar_convite(
        remetente_id, remetente_nome, data.email
    )
    if result["status"] == 400:
        raise HTTPException(status_code=400, detail=result["erro"])
    return {"sucesso": result["sucesso"]}


# GET: /convites/exportar-csv (para admin)
@router.get("/exportar-csv", status_code=200)
async def exportar_convites_csv(
    current_user: Dict = Depends(get_current_admin_user), # Somente admin
):
    csv_data = await convites_service.exportar_convites_csv()

    if csv_data is None:
        raise HTTPException(status_code=204, detail="Nenhum convite para exportar.")

    response = StreamingResponse(
        io.StringIO(csv_data),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=convites.csv"},
    )
    return response


# GET: /convites/{remetente_uuid}
@router.get("/{remetente_uuid}")
async def listar_convites_por_remetente(
    remetente_uuid: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    destinatario: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    dt_envio: Optional[str] = Query(None),
    current_user: Dict = Depends(get_current_user), # Autenticação para qualquer usuário
):
    # Verifica se o usuário logado está tentando ver os próprios convites
    if current_user["id"] != remetente_uuid:
        # Ou se é admin e pode ver convites de outros
        if not current_user.get("admin"):
            raise HTTPException(status_code=403, detail="Acesso negado: Você só pode ver seus próprios convites")

    filtros = {}
    if destinatario:
        filtros["destinatario"] = destinatario
    if status:
        filtros["status"] = status
    if dt_envio:
        filtros["dt_envio"] = dt_envio

    result = await convites_service.listar_convites_por_remetente(
        remetente_uuid, page, per_page, filtros
    )
    if result["status"] == 204:
        return {"sucesso": result["sucesso"], "convites": [], "registros": 0, "convertidos": 0, "pendentes": 0, "page": page, "pages": 1, "per_page": per_page, "prev_page": False, "prox_page": False}
    if result["status"] == 200:
        return result["data"]
    raise HTTPException(status_code=500, detail="Erro interno do servidor")


# GET: /convites (para admin)
@router.get("/")
async def listar_todos_convites(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    remetente: Optional[str] = Query(None),
    destinatario: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    dt_envio: Optional[str] = Query(None),
    current_user: Dict = Depends(get_current_admin_user), # Autenticação para admin
):
    filtros = {}
    if remetente:
        filtros["remetente"] = remetente
    if destinatario:
        filtros["destinatario"] = destinatario
    if status:
        filtros["status"] = status
    if dt_envio:
        filtros["dt_envio"] = dt_envio

    result = await convites_service.listar_todos_convites(page, per_page, filtros)
    if result["status"] == 204:
        return {"sucesso": result["sucesso"], "convites": [], "registros": 0, "page": page, "pages": 1, "per_page": per_page, "prev_page": False, "prox_page": False}
    if result["status"] == 200:
        return result["data"]
    raise HTTPException(status_code=500, detail="Erro interno do servidor")