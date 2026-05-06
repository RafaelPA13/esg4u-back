from fastapi import APIRouter, HTTPException, Header, Depends, UploadFile, File, Form
from src.services.auth_service import auth_service
from src.services.evidencias_service import evidencias_service

router = APIRouter(prefix="/evidencias", tags=["Evidências"])


async def get_current_user(authorization: str = Header(...)):
    user_info = await auth_service.me(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="Credenciais expiradas, logue novamente")
    return user_info


# GET /evidencias/minhas-evidencias
@router.get("/minhas-evidencias")
async def minhas_evidencias(current_user: dict = Depends(get_current_user)):
    result = await evidencias_service.listar_minhas_evidencias(current_user["id"])
    return result["data"]


# GET /evidencias/{id}
@router.get("/{evidencia_id}")
async def buscar_evidencia(
    evidencia_id: int,
    current_user: dict = Depends(get_current_user),
):
    result = await evidencias_service.buscar_evidencia(evidencia_id)
    if result["status"] == 404:
        raise HTTPException(status_code=404, detail=result["erro"])
    return result["data"]


# POST /evidencias/adicionar
@router.post("/adicionar", status_code=201)
async def adicionar_evidencia(
    evidencia: UploadFile = File(...),
    id_resposta: str = Form(...),
    current_user: dict = Depends(get_current_user),
):
    file_bytes = await evidencia.read()
    result = await evidencias_service.adicionar_evidencia(
        id_resposta=int(id_resposta),
        file_bytes=file_bytes,
        file_name=evidencia.filename,
        content_type=evidencia.content_type,
        usuario_id=current_user["id"],
    )
    if result["status"] == 404:
        raise HTTPException(status_code=404, detail=result["erro"])
    if result["status"] == 500:
        raise HTTPException(status_code=500, detail=result["erro"])
    return {"sucesso": result["sucesso"]}