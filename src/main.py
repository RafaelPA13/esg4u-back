from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from src.api.auth_routes import router as auth_router
from src.api.diagnostico_routes import router as diagnostico_router

app = FastAPI(
    title="ESG4U API",
    description="API do ESG4U",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router)
app.include_router(diagnostico_router)


@app.get("/")
def health_check():
    return {"status": "ok", "message": "ESG4U API rodando"}

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    # Pega a primeira mensagem de erro de validação
    try:
        mensagem = exc.errors()[0]["msg"].replace("Value error, ", "")
    except (IndexError, KeyError):
        mensagem = "Dados inválidos."
    return JSONResponse(status_code=422, content={"erro": mensagem})