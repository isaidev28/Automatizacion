import jwt
import time
import uuid
import requests
import json
import logging
from pathlib import Path
from typing import Optional
from src.domain.ports.outbound.i_sala_service import ISalaService, LinksSala

logger = logging.getLogger(__name__)

class JitsiAdapter(ISalaService):

    def __init__(self, app_id: str, api_key_id: str, private_key_path: str, api_base_url: str = None):
        self._app_id         = app_id
        self._api_key_id     = api_key_id
        self._private_key    = Path(private_key_path).read_text()
        self._base_url       = "https://8x8.vc"
        self._api_base_url   = api_base_url or "https://api.8x8.vc/v1"
        self._salas_creadas  = set()

    def _generar_token_para_api(self, metodo: str, ruta: str) -> str:
        ahora = int(time.time())
        payload = {
            "aud": "jitsi",
            "iss": "chat",
            "iat": ahora,
            "exp": ahora + (60 * 5),
            "sub": self._app_id,
            "admin": True,
        }
        return jwt.encode(
            payload,
            self._private_key,
            algorithm="RS256",
            headers={"kid": self._api_key_id}
        )

    async def _crear_sala_en_8x8(self, sala_id: str) -> bool:
        """En JaaS las salas se crean automáticamente al unirse con JWT válido"""
        logger.info(f"Sala {sala_id} se creará automáticamente en JaaS al unirse")
        return True

    def _generar_token_usuario(
        self,
        sala_id: str,
        nombre: str,
        correo: str,
        es_moderador: bool
    ) -> str:
        ahora = int(time.time())
        expiracion = ahora + (60 * 60 * 2)

        payload = {
            "aud": "jitsi",
            "iss": "chat",
            "iat": ahora,
            "exp": expiracion,
            "nbf": ahora - 5,
            "sub": self._app_id,
            "context": {
                "user": {
                    "name": nombre,
                    "email": correo,
                    "moderator": str(es_moderador).lower(),
                    "id": str(uuid.uuid4()),
                },
                "features": {
                    "recording": str(es_moderador).lower(),
                    "livestreaming": "false",
                    "outbound-call": "false",
                    "transcription": "false",
                }
            },
            "moderator": es_moderador,
            "room": sala_id,  # ✅ solo nombre, sin app_id
        }

        return jwt.encode(
            payload,
            self._private_key,
            algorithm="RS256",
            headers={"kid": self._api_key_id}
        )

    def generar_token_alumno(self, sala_id: str, nombre: str, correo: str) -> str:
        return self._generar_token_usuario(
            sala_id      = sala_id,
            nombre       = nombre,
            correo       = correo,
            es_moderador = False
        )

    def generar_token_moderador(self, sala_id: str, nombre: str) -> str:
        return self._generar_token_usuario(
            sala_id      = sala_id,
            nombre       = nombre,
            correo       = "ia@clase.com",
            es_moderador = True
        )

    async def crear_sala(
        self,
        sala_id: str,
        nombre_profesor: str,
        nombre_alumno: str,
        correo_alumno: str,
    ) -> LinksSala:

        sala_creada = await self._crear_sala_en_8x8(sala_id)
        if not sala_creada:
            logger.warning(f"No se pudo crear la sala {sala_id}, pero intentaremos continuar")

        token_alumno    = self.generar_token_alumno(sala_id, nombre_alumno, correo_alumno)
        token_moderador = self.generar_token_moderador(sala_id, nombre_profesor)

        link_alumno = (
            f"{self._base_url}/{self._app_id}/{sala_id}"
            f"?jwt={token_alumno}"
            f"&config.knocking=true"
            f"&userInfo.displayName={nombre_alumno}"
        )

        link_supervisor = (
            f"{self._base_url}/{self._app_id}/{sala_id}"
            f"?jwt={token_moderador}"
            f"&config.knocking=false"
            f"&config.prejoinPageEnabled=false"
            f"&userInfo.displayName={nombre_profesor}"
        )

        logger.info(f"Sala {sala_id} lista. Links generados.")

        return LinksSala(
            alumno     = link_alumno,
            supervisor = link_supervisor,
            sala_id    = sala_id
        )

    async def cerrar_sala(self, sala_id: str) -> bool:
        try:
            api_token = self._generar_token_para_api("DELETE", f"/rooms/{sala_id}")
            headers   = {'Authorization': f'Bearer {api_token}'}
            url       = f"{self._api_base_url}/rooms/{self._app_id}/{sala_id}"

            response = requests.delete(url, headers=headers, timeout=10)

            if response.status_code in [200, 204]:
                logger.info(f"Sala {sala_id} cerrada exitosamente")
                self._salas_creadas.discard(sala_id)
                return True
            else:
                logger.warning(f"Error cerrando sala {sala_id}: {response.status_code}")
                return False

        except Exception as e:
            logger.exception(f"Excepción cerrando sala {sala_id}")
            return False