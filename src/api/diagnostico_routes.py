from fastapi import APIRouter, HTTPException, Header, Depends
from fastapi.responses import StreamingResponse
from src.schemas.diagnostico_schema import PerguntaSchema
import io

from src.services.auth_service import auth_service
from src.services.diagnostico_service import diagnostico_service

router = APIRouter(prefix="/diagnostico", tags=["Diagnóstico"])


# Dependência de admin (reutiliza o padrão já existente no projeto)
async def get_current_admin_user(authorization: str = Header(...)):
    user_info = await auth_service.me(authorization)
    if not user_info or not user_info.get("admin"):
        raise HTTPException(status_code=401, detail="Usuário não autorizado")
    return user_info


# POST /diagnostico/pergunta
@router.post("/pergunta", status_code=201)
async def criar_pergunta(
    payload: PerguntaSchema,
    admin_user: dict = Depends(get_current_admin_user),
):
    result = await diagnostico_service.criar_pergunta(payload.model_dump())

    if result["status"] == 409:
        raise HTTPException(status_code=409, detail=result["erro"])

    return {"sucesso": result["sucesso"]}


# GET /diagnostico/perguntas/exportar-csv
@router.get("/perguntas/exportar-csv")
async def exportar_perguntas_csv(
    admin_user: dict = Depends(get_current_admin_user),
):
    csv_content = await diagnostico_service.exportar_csv()

    if csv_content is None:
        raise HTTPException(status_code=204, detail="Nenhum registro encontrado.")

    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=perguntas.csv"},
    )


# GET /diagnostico/perguntas
@router.get("/perguntas")
async def listar_perguntas(
    admin_user: dict = Depends(get_current_admin_user),
):
    result = await diagnostico_service.listar_perguntas()

    if result["status"] == 204:
        raise HTTPException(status_code=204, detail=result["sucesso"])

    return result["data"]


# GET /diagnostico/pergunta/{id}
@router.get("/pergunta/{pergunta_id}")
async def buscar_pergunta(
    pergunta_id: int,
    admin_user: dict = Depends(get_current_admin_user),
):
    result = await diagnostico_service.buscar_pergunta(pergunta_id)

    if result["status"] == 204:
        raise HTTPException(status_code=204, detail=result["sucesso"])

    return result["data"]


# PUT /diagnostico/pergunta/{id}
@router.put("/pergunta/{pergunta_id}")
async def atualizar_pergunta(
    pergunta_id: int,
    payload: PerguntaSchema,
    admin_user: dict = Depends(get_current_admin_user),
):
    result = await diagnostico_service.atualizar_pergunta(
        pergunta_id, payload.model_dump()
    )

    if result["status"] == 404:
        raise HTTPException(status_code=404, detail=result["erro"])

    return {"sucesso": result["sucesso"]}


# DELETE /diagnostico/pergunta/{id}
@router.delete("/pergunta/{pergunta_id}", status_code=204)
async def deletar_pergunta(
    pergunta_id: int,
    admin_user: dict = Depends(get_current_admin_user),
):
    result = await diagnostico_service.deletar_pergunta(pergunta_id)

    if result["status"] == 404:
        raise HTTPException(status_code=404, detail=result["erro"])

    return None  # 204 não retorna corpo