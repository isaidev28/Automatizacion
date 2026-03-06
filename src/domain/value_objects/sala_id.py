import re 
from dataclasses import dataclass

@dataclass(frozen=True)
class SalaId:
    valor: str

    def __post_init__(self):
        if not self.valor or len(self.valor) < 5:
            raise ValueError("SalaId debe tener 5 caracteres minimo")
        if not re.match(r'^[a-zA-Z0-9_-]+$', self.valor):
            raise ValueError("SalaId solo puede conteneter letras, numeros, guiones y guiones bajos")
        
    def __str__(self):
        return self.valor
    