from pydantic import BaseModel
from typing import Optional

class PerguntaSchema(BaseModel):
    indice: int
    ativa: bool
    eixo_esg: str
    tema: str
    pergunta: str
    exemplo: Optional[str] = None