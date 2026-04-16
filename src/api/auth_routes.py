from fastapi import APIRouter, HTTPException, Form
from src.schemas.auth_schema import CadastroSchema, LoginSchema
from src.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


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