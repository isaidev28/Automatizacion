import re
from dataclasses import dataclass

@dataclass(frozen=True)
class Email:
    valor: str

    def __post_init__(self):
        patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(patron, self.valor):
            raise ValueError(f"Email invalido: {self.valor}")
        
    def __str__(self):
        return self.valor