import json
import io
from fastapi.responses import StreamingResponse
from fastapi import APIRouter, Depends, File, Form, Header, Response, UploadFile, status, Query

from src.services.bugs_service import bugs_service
from src.services.auth_service import auth_service

router = APIRouter(prefix="/bugs", tags=["Bugs"])


# --- Dependências de autenticação ---

async def get_current_user(authorization: str = Header(None)):
    if not authorization:
        return None
    try:
        return await auth_service.me(authorization)
    except Exception:
        return None


async def get_current_admin_user(authorization: str = Header(None)):
    if not authorization:
        return None
    try:
        user = await auth_service.me(authorization)
        if not user or not user.get("admin"):
            return None
        return user
    except Exception:
        return None


def unauthorized():
    return Response(
        content='{"erro":"Credenciais inválidas ou expiradas"}',
        status_code=status.HTTP_401_UNAUTHORIZED,
        media_type="application/json",
    )


# --- Endpoints ---

@router.post("/reportar_bug")
async def reportar_bug_endpoint(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    titulo: str = Form(...),
    descricao: str = Form(...),
    current_user: dict = Depends(get_current_user),
):
    """
    Recebe o print como arquivo e os demais campos via form-data.
    RN2: qualquer usuário logado pode acessar.
    """
    if not current_user:
        return unauthorized()

    file_bytes = await file.read()
    filename = f"{current_user['id']}_{file.filename}"
    content_type = file.content_type or "image/png"

    result = await bugs_service.reportar_bug(
        user_id=user_id,
        titulo=titulo,
        descricao=descricao,
        file_bytes=file_bytes,
        filename=filename,
        content_type=content_type,
    )

    
    status_code = result.pop("status", status.HTTP_400_BAD_REQUEST)
    content = result.get("erro") or result.get("sucesso")
    key = "sucesso" if "sucesso" in result else "erro"
    return Response(
        content=json.dumps({key: content}, ensure_ascii=False),
        status_code=status_code,
        media_type="application/json",
    )


@router.get("/exportar_csv")
async def exportar_bugs_csv_endpoint(
    admin_user: dict = Depends(get_current_admin_user),
):
    """
    Exporta todos os bugs em CSV. Somente admin.
    Declarado antes de /listar para evitar conflito de rota.
    """
    if not admin_user:
        return unauthorized()

    csv_content = await bugs_service.exportar_csv()
    if csv_content is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=bugs.csv"},
    )


@router.put("/{bug_id}")
async def atualizar_status_endpoint(
    bug_id: int,
    payload: dict,
    admin_user: dict = Depends(get_current_admin_user),
):
    """
    Atualiza o status de um bug. RN1: somente admin.
    """
    if not admin_user:
        return unauthorized()

    novo_status = payload.get("status")
    if not novo_status:
        return Response(
            content='{"erro":"Campo status é obrigatório"}',
            status_code=status.HTTP_400_BAD_REQUEST,
            media_type="application/json",
        )

    result = await bugs_service.atualizar_status(bug_id, novo_status)

    status_code = result.pop("status", status.HTTP_400_BAD_REQUEST)
    content = result.get("erro") or result.get("sucesso")
    key = "sucesso" if "sucesso" in result else "erro"
    return Response(
        content=json.dumps({key: content}, ensure_ascii=False),
        status_code=status_code,
        media_type="application/json",
    )


@router.get("/listar")
async def listar_bugs_endpoint(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    status_filtro: str = Query(None, alias="status"),
    dt_inicio: str = Query(None, description="Data início no formato ISO 8601, ex: 2026-01-01"),
    dt_fim: str = Query(None, description="Data fim no formato ISO 8601, ex: 2026-12-31"),
    admin_user: dict = Depends(get_current_admin_user),
):
    """
    Lista paginada de bugs com filtros. RN2: somente admin.
    """
    if not admin_user:
        return unauthorized()

    result = await bugs_service.listar(
        page=page,
        per_page=per_page,
        filtro_status=status_filtro,
        dt_inicio=dt_inicio,
        dt_fim=dt_fim,
    )

    status_code = result.pop("status", status.HTTP_400_BAD_REQUEST)
    if status_code == 204:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    content = result.get("erro") or result.get("data")
    return Response(
        content=json.dumps(content, ensure_ascii=False),
        status_code=status_code,
        media_type="application/json",
    )