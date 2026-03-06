from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

@dataclass
class SesionIA:
    clase_id: str
    historial_chat: list[dict] = field (default_factory=list)
    progreso: float = 0.0
    ultimo_checkpoint = str = "" #ultimo tema explicado
    esperando_respuesta_alumno: bool = False
    pausas_sin_respuesta: int = 0 #cuantas veces pregunto sin respuesta
    creada_en: datetime = field(default_factory=datetime.utcnow)

    MAX_HISTORIAL = 50
    MAX_PAUSAS_SIN_RESPUESTA = 3 #despues de 3 intentos continua

    def agregar_mensaje(self, rol: str, contenido: str):
        self.historial_chat.append({
            "role": rol,
            "content": contenido,
            "timestamp": datetime.utcnow().isoformat()
        })
        #Mantener solo los ultimos mensajes
        if len(self.historial_chat) > self.MAX_HISTORIAL:
            self.historial_chat = self.historial_chat[-self.MAX_HISTORIAL:]
    
    def avanzar_progreso(self, incremento: float = 5.0):
        self.progreso = min(100.0, self.progreso + incremento)

    def debe_preguntar_dudas(self) -> bool:
        """cada 20% de progreso la IA debe preguntar si hay dudas"""
        checkpoints = [20.0, 40.0, 60.0, 80.0, 100.0]
        return any (
            self.progreso >= cp and self.ultimo_checkpoint != str(cp)
            for cp in checkpoints
        )
    
    def marcar_checkpoint(self):
        checkpoints = [20.0, 40.0, 60.0, 80.0, 100.0]
        for cp in checkpoints:
            if self.progreso >= cp:
                self.ultimo_checkpoint = str(cp)