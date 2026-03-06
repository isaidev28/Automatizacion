from src.domain.ports.outbound.i_sala_service import ISalaService
from src.domain.ports.outbound.i_cache_service import ICacheService


class FinalizarClaseUseCase:

    def __init__(
        self,
        sala_service:  ISalaService,
        cache_service: ICacheService,
    ):
        self._sala  = sala_service
        self._cache = cache_service

    async def ejecutar(self, clase_id: str) -> dict:
        sesion = await self._cache.obtener_sesion(clase_id)
        if not sesion:
            raise ValueError(f"Clase {clase_id} no encontrada")

        sala_id = sesion.get("sala_id", "")

        await self._sala.cerrar_sala(sala_id)
        await self._cache.actualizar_estado(clase_id, "finalizada")
        await self._cache.eliminar_sesion(clase_id)

        return {
            "clase_id": clase_id,
            "sala_id":  sala_id,
            "estado":   "finalizada",
            "mensaje":  "Clase finalizada y recursos liberados"
        }