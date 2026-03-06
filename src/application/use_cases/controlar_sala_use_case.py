from src.domain.ports.outbound.i_sala_service import ISalaService
from src.domain.ports.outbound.i_cache_service import ICacheService
from src.domain.ports.inbound.i_controlar_sala import IControlarSala
from src.domain.exceptions.clase_exception import ClaseYaFinalizadaException


class ControlarSalaUseCase(IControlarSala):

    def __init__(
        self,
        sala_service:  ISalaService,
        cache_service: ICacheService,
    ):
        self._sala  = sala_service
        self._cache = cache_service

    async def pausar_ia(self, clase_id: str) -> None:
        sesion = await self._cache.obtener_sesion(clase_id)
        if not sesion:
            raise ValueError(f"Clase {clase_id} no encontrada")
        if sesion.get("estado") == "finalizada":
            raise ClaseYaFinalizadaException("La clase ya finalizó")

        await self._cache.actualizar_estado(clase_id, "en_pausa_ia")
        await self._cache.publicar_evento(
            f"canal:clase:{clase_id}",
            {"evento": "IA_PAUSADA", "clase_id": clase_id}
        )

    async def reanudar_ia(self, clase_id: str) -> None:
        await self._cache.actualizar_estado(clase_id, "en_curso")
        await self._cache.publicar_evento(
            f"canal:clase:{clase_id}",
            {"evento": "IA_REANUDADA", "clase_id": clase_id}
        )

    async def finalizar_clase(self, clase_id: str) -> None:
        sesion = await self._cache.obtener_sesion(clase_id)
        if not sesion:
            raise ValueError(f"Clase {clase_id} no encontrada")

        # Cerrar sala en Jitsi
        await self._sala.cerrar_sala(sesion.get("sala_id", ""))

        # Marcar como finalizada y limpiar Redis
        await self._cache.actualizar_estado(clase_id, "finalizada")
        await self._cache.publicar_evento(
            f"canal:clase:{clase_id}",
            {"evento": "CLASE_FINALIZADA", "clase_id": clase_id}
        )
        await self._cache.eliminar_sesion(clase_id)