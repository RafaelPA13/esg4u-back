from pydantic import BaseModel, field_validator
from typing import Optional, List

PONTUACOES_VALIDAS = {0, 1, 2, 3, 4}

class PerguntaSchema(BaseModel):
    indice: int
    ativa: bool
    eixo_esg: str
    tema: str
    pergunta: str
    exemplo: Optional[str] = None

    
class RespostaLoteItemSchema(BaseModel):
    id_pergunta: int
    respondido_por: str
    pontuacao: int

    @field_validator("pontuacao")
    @classmethod
    def validar_pontuacao(cls, v):
        if v not in PONTUACOES_VALIDAS:
            raise ValueError(
                "Pontuação inválida. Use: 0 (Nunca), 1 (Raramente), "
                "2 (Às vezes), 3 (Frequentemente) ou 4 (Sempre)."
            )
        return v


class RespostaLoteSchema(BaseModel):
    respostas: List[RespostaLoteItemSchema]