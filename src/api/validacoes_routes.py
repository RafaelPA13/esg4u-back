import json
from fastapi import APIRouter, Depends, Header, Response, status
from typing import Dict, Any

from src.services.validacoes_service import validacoes_service
from src.services.auth_service import auth_service

router = APIRouter(prefix="/validacoes", tags=["Validações"])


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