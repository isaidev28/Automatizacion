from dataclasses import dataclass

@dataclass
class ControlarSalaDTO:
    clase_id: str
    accion: str     # "pausar" | "reanudar" | "finalizar"

@dataclass
class RespuestaControlarSalaDTO:
    clase_id: str
    accion_ejecutada: str
    estado_actual: str
    mensaje: str