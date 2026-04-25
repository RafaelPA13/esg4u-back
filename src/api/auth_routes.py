from fastapi import APIRouter, HTTPException, Form, Header, Query, Depends, Request
from src.schemas.auth_schema import CadastroSchema, LoginSchema, UserResponseSchema, UserUpdateSchema
from src.services.auth_service import auth_service
from typing import Dict, Any
from uuid import UUID

router = APIRouter(prefix="/auth", tags=["Auth"])


# Dependência para verificar se o usuário é admin
async def get_current_admin_user(authorization: str = Header(...)):
    user_info = await auth_service.me(authorization)
    if not user_info or not user_info.get("admin"):
        raise HTTPException(status_code=401, detail="Usuário não autorizado")
    return user_info


@router.post("/cadastro", status_code=201)
async def cadastro(payload: CadastroSchema):
    try:
        result = await auth_service.cadastrar(payload)
        return result
    except Exception as e:
        if "E-mail já cadastrado" in str(e):
            raise HTTPException(status_code=409, detail=str(e))
        if "senhas" in str(e):
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/validar_codigo")
async def validar_codigo(codigo: str = Form(...)):
    try:
        result = await auth_service.validar_codigo(codigo)
        return result
    except Exception as e:
        if "expirado" in str(e):
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    

@router.post("/reenviar_codigo")
async def reenviar_codigo(email: str = Form(...)):
    try:
        return await auth_service.reenviar_codigo(email)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    

@router.post("/solicitar_reset")
async def solicitar_reset(email: str = Form(...)):
    try:
        return await auth_service.solicitar_reset(email)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/redefinir_senha")
async def redefinir_senha(
    token: str = Form(...),
    senha: str = Form(...),
    confirmar_senha: str = Form(...)
):
    try:
        return await auth_service.redefinir_senha(
            token,
            senha,
            confirmar_senha
        )
    except Exception as e:
        if "idênticas" in str(e):
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    
    
@router.post("/login")
async def login(data: LoginSchema):
    try:
        result = await auth_service.login(
            data.email,
            data.senha
        )
        return result
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Credenciais inválidas"
        )
        
        
@router.get("/me")
async def me(authorization: str = Header(...)):
    try:
        return await auth_service.me(authorization)
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))
    
@router.get("/usuarios", response_model=Dict[str, Any])
async def get_all_users_endpoint(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    admin_user: dict = Depends(get_current_admin_user),
):
    # Extrai todos os parâmetros de query da request
    all_query_params = dict(request.query_params)

    # Remove os parâmetros de paginação para deixar apenas os filtros
    filters = {k: v for k, v in all_query_params.items() if k not in ["page", "per_page"]}

    result = await auth_service.get_all_users(page, per_page, filters)

    if result is None:
        raise HTTPException(status_code=204, detail="Nenhum registro encontrado")
    return result

@router.get("/usuario/{user_id}", response_model=UserResponseSchema)
async def get_user_by_id_endpoint(
    user_id: UUID,
    admin_user: dict = Depends(get_current_admin_user)
):
    user = await auth_service.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=204, detail="Nenhum registro encontrado")
    return user

@router.put("/usuario/{user_id}")
async def update_user_endpoint(
    user_id: UUID,
    user_data: UserUpdateSchema,
    admin_user: dict = Depends(get_current_admin_user)
):
    try:
        await auth_service.update_user_data(user_id, user_data)
        return {"message": "Usuário Atualizado."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/usuario/{user_id}")
async def delete_user_endpoint(
    user_id: UUID,
    admin_user: dict = Depends(get_current_admin_user)
):
    try:
        await auth_service.delete_user_by_id(user_id)
        return {"message": "Usuário Excluído."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))