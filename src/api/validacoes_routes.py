import json
import io
from fastapi import APIRouter, Depends, Header, Response, status, Query
from fastapi.responses import StreamingResponse
from typing import Dict, Any

from src.services.validacoes_service import validacoes_service
from src.services.auth_service import auth_service

router = APIRouter(prefix="/validacoes", tags=["Validações"])


# Adicionar dependência de admin (mesmo padrão do projeto)
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


async def get_current_user(authorization: str = Header(None)):
    if not authorization:
        return None
    try:
        return await auth_service.me(authorization)
    except Exception:
        return None


def unauthorized():
    return Response(
        content='{"erro":"Credenciais expiradas, logue novamente"}',
        status_code=status.HTTP_401_UNAUTHORIZED,
        media_type="application/json",
    )

def forbidden(msg: str = "Acesso não autorizado"):
    return Response(
        content=f'{{"erro":"{msg}"}}',
        status_code=status.HTTP_403_FORBIDDEN,
        media_type="application/json",
    )


@router.post("/pedir_validacao")
async def pedir_validacao_endpoint(
    payload: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not current_user:
        return unauthorized()

    result = await validacoes_service.pedir_validacao(
        payload, usuario_email=current_user["email"]
    )

    status_code = result.pop("status", status.HTTP_400_BAD_REQUEST)
    content = result.get("erro") or result.get("sucesso")
    return Response(
        content=json.dumps({"sucesso": content} if "sucesso" in result or not result.get("erro") else {"erro": content}, ensure_ascii=False),
        status_code=status_code,
        media_type="application/json",
    )


@router.put("/validar/{validacao_id}")
async def validar_validacao_endpoint(
    validacao_id: int,
    payload: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not current_user:
        return unauthorized()

    result = await validacoes_service.validar(validacao_id, payload)

    status_code = result.pop("status", status.HTTP_400_BAD_REQUEST)
    content = result.get("erro") or result.get("sucesso")
    return Response(
        content=json.dumps({"sucesso": content} if "sucesso" in result else {"erro": content}, ensure_ascii=False),
        status_code=status_code,
        media_type="application/json",
    )
  
  
@router.get("/")
async def listar_todas_validacoes_endpoint(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    pedido_por: str = Query(None),   # filtra por nome
    avaliador: str = Query(None),    # filtra por email
    admin_user: dict = Depends(get_current_admin_user),
):
    """
    Lista paginada de todas as validações. Requer admin.
    Deve ser declarado ANTES de /{avaliador_email} para evitar conflito de rota.
    """
    if not admin_user:
        return unauthorized()

    result = await validacoes_service.listar_todas_admin(
        page=page,
        per_page=per_page,
        filtro_pedido_por=pedido_por,
        filtro_avaliador=avaliador,
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
    
    
@router.get("/exportar_csv")
async def exportar_validacoes_csv_endpoint(
    admin_user: dict = Depends(get_current_admin_user),
):
    """
    Exporta todas as validações em CSV. Requer admin.
    Deve ser declarado ANTES de /{avaliador_email} para evitar conflito de rota.
    """
    if not admin_user:
        return unauthorized()

    csv_content = await validacoes_service.exportar_validacoes_csv()
    if csv_content is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=validacoes.csv"},
    )


@router.get("/minhas_validacoes/{pedido_por_email}")
async def listar_minhas_validacoes_endpoint(
    pedido_por_email: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not current_user:
        return unauthorized()

    if current_user["email"] != pedido_por_email:
        return forbidden()

    result = await validacoes_service.listar_minhas_validacoes(pedido_por_email)

    status_code = result.pop("status", status.HTTP_400_BAD_REQUEST)
    if status_code == 204:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    content = result.get("erro") or result.get("data")
    return Response(
        content=json.dumps(content, ensure_ascii=False),
        status_code=status_code,
        media_type="application/json",
    )


@router.get("/{avaliador_email}")
async def listar_por_avaliador_endpoint(
    avaliador_email: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not current_user:
        return unauthorized()

    if current_user["email"] != avaliador_email:
        return forbidden()

    result = await validacoes_service.listar_por_avaliador(avaliador_email)

    status_code = result.pop("status", status.HTTP_400_BAD_REQUEST)
    if status_code == 204:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    content = result.get("erro") or result.get("data")
    return Response(
        content=json.dumps(content, ensure_ascii=False),
        status_code=status_code,
        media_type="application/json",
    )