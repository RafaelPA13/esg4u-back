from pydantic import BaseModel
from uuid import UUID


class DashboardAdminSchema(BaseModel):
    total_usuarios: int
    score_esg_medio: float
    evidencias_anexadas: int
    validacoes_pendentes: int
    convites_enviados: int
    taxa_conversao_convites: float
    bugs_reportados: int
    
class RankingUsuarioSchema(BaseModel):
    posicao: int
    id: UUID
    nome: str
    foto_perfil: str | None = None
    score_esg: float


class RankingResponseSchema(BaseModel):
    top_10: list[RankingUsuarioSchema]
    minha_posicao: RankingUsuarioSchema | None