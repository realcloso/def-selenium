from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class Produto:
    nome: str
    preco: float
    relevancia: int = 0
    avaliacao: float = 0.0
    link: str = ""
    detalhes: Dict[str, str] = field(default_factory=dict)
    filtros_pesquisados: List[str] = field(default_factory=list)
    ranking: Optional[float] = None  # Changed to float for weighted score