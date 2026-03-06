import redis
import json
from src.domain.ports.outbound.i_cache_service import ICacheService
from typing import Optional
import asyncio


class RedisAdapter(ICacheService):

    def __init__(self, url: str):
        self._url = url

    def _get_client(self) -> redis.Redis:
        return redis.from_url(
            self._url,
            decode_responses = True,
            socket_timeout   = 5
        )

    # ========================
    # Helpers síncronos
    # ========================

    def _guardar_sesion_sync(self, clase_id: str, datos: dict, ttl: int) -> None:
        r = self._get_client()
        r.setex(f"clase:{clase_id}:sesion", ttl, json.dumps(datos, default=str))

    def _obtener_sesion_sync(self, clase_id: str) -> Optional[dict]:
        r    = self._get_client()
        data = r.get(f"clase:{clase_id}:sesion")
        return json.loads(data) if data else None

    def _actualizar_estado_sync(self, clase_id: str, estado: str) -> None:
        r = self._get_client()
        r.hset(f"clase:{clase_id}:estado", mapping={"ia_estado": estado})
        r.expire(f"clase:{clase_id}:estado", 7200)

    def _guardar_historial_sync(self, clase_id: str, mensaje: dict) -> None:
        r = self._get_client()
        r.rpush(f"clase:{clase_id}:historial", json.dumps(mensaje))
        r.ltrim(f"clase:{clase_id}:historial", -50, -1)

    def _obtener_historial_sync(self, clase_id: str) -> list[dict]:
        r        = self._get_client()
        mensajes = r.lrange(f"clase:{clase_id}:historial", 0, -1)
        return [json.loads(m) for m in mensajes]

    def _eliminar_sesion_sync(self, clase_id: str) -> None:
        r    = self._get_client()
        keys = [
            f"clase:{clase_id}:sesion",
            f"clase:{clase_id}:estado",
            f"clase:{clase_id}:historial",
        ]
        r.delete(*keys)

    def _ping_sync(self) -> bool:
        r = self._get_client()
        return r.ping()

    # ========================
    # Interface async
    # ========================

    async def guardar_sesion(self, clase_id: str, datos: dict, ttl: int = 7200) -> None:
        await asyncio.to_thread(self._guardar_sesion_sync, clase_id, datos, ttl)

    async def obtener_sesion(self, clase_id: str) -> Optional[dict]:
        return await asyncio.to_thread(self._obtener_sesion_sync, clase_id)

    async def actualizar_estado(self, clase_id: str, estado: str) -> None:
        await asyncio.to_thread(self._actualizar_estado_sync, clase_id, estado)

    async def guardar_historial_chat(self, clase_id: str, mensaje: dict) -> None:
        await asyncio.to_thread(self._guardar_historial_sync, clase_id, mensaje)

    async def obtener_historial_chat(self, clase_id: str) -> list[dict]:
        return await asyncio.to_thread(self._obtener_historial_sync, clase_id)

    async def publicar_evento(self, canal: str, evento: dict) -> None:
        pass  # Sin async Redis por ahora

    async def suscribir_canal(self, canal: str):
        pass  # Sin async Redis por ahora

    async def eliminar_sesion(self, clase_id: str) -> None:
        await asyncio.to_thread(self._eliminar_sesion_sync, clase_id)

    async def ping(self) -> bool:
        return await asyncio.to_thread(self._ping_sync)