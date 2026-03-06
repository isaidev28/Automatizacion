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
        self._app_id          = app_id
        self._api_key_id      = api_key_id
        self._private_key     = Path(private_key_path).read_text()
        self._base_url        = "https://8x8.vc"
        
        # URL base para las APIs de 8x8 (verifica en tu dashboard)
        self._api_base_url = api_base_url or "https://api.8x8.com/v1"
        
        # Cache para evitar crear la misma sala múltiples veces
        self._salas_creadas = set()

    def _generar_token_para_api(self, metodo: str, ruta: str) -> str:
        """Genera un token para autenticarse con la API de 8x8 (no para usuarios)"""
        ahora = int(time.time())
        
        payload = {
            "aud": "jitsi",
            "iss": "chat",
            "iat": ahora,
            "exp": ahora + (60 * 5),  # 5 minutos es suficiente para la llamada API
            "sub": self._app_id,
            "room": "*",  # El * permite acceso a cualquier sala para crear
            "context": {
                "user": {
                    "name": "api-service",
                    "email": "api@clase.com",
                    "moderator": "true",  # Necesita permisos de admin
                },
                "features": {
                    "recording": "true",
                    "livestreaming": "false",
                    "outbound-call": "false",
                    "transcription": "false",
                }
            },
            "moderator": True
        }
        
        token = jwt.encode(
            payload,
            self._private_key,
            algorithm="RS256",
            headers={"kid": self._api_key_id}
        )
        return token

    async def _crear_sala_en_8x8(self, sala_id: str) -> bool:
        """Crea la sala explícitamente en el backend de 8x8"""
        
        if sala_id in self._salas_creadas:
            logger.info(f"Sala {sala_id} ya fue creada previamente")
            return True
        
        try:
            # Generar token para la API
            api_token = self._generar_token_para_api("POST", "/rooms")
            
            # Configurar headers
            headers = {
                'Authorization': f'Bearer {api_token}',
                'Content-Type': 'application/json'
            }
            
            # Configuración de la sala
            room_config = {
                "name": f"{self._app_id}/{sala_id}",  # Importante: incluir app_id
                "privacy": "private",  # privada = requiere JWT
                "properties": {
                    "enable_knocking": True,          # Permitir "tocar la puerta"
                    "enable_chat": True,
                    "enable_screen_sharing": True,
                    "start_audio_off": False,
                    "start_video_off": False,
                    "max_participants": 50,
                    "exp": int(time.time()) + (60 * 60 * 2),  # 2 horas
                    "enable_waiting_room": True,      # Sala de espera
                    "require_authenticated_participants": True,  # Requiere JWT
                    "auto_knocking": True,            # Auto-aprobar si es moderador
                    "enable_prejoin_ui": True
                }
            }
            
            # Endpoint para crear sala
            url = f"{self._api_base_url}/rooms"
            
            logger.info(f"Creando sala en 8x8: {sala_id}")
            
            # Hacer la petición
            response = requests.post(
                url,
                json=room_config,
                headers=headers,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Sala {sala_id} creada exitosamente")
                self._salas_creadas.add(sala_id)
                return True
            elif response.status_code == 409:
                # La sala ya existe, es un error aceptable
                logger.info(f"Sala {sala_id} ya existía en el backend")
                self._salas_creadas.add(sala_id)
                return True
            else:
                logger.error(f"Error creando sala {sala_id}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.exception(f"Excepción creando sala {sala_id}")
            return False

    def _generar_token_usuario(
        self,
        sala_id: str,
        nombre: str,
        correo: str,
        es_moderador: bool
    ) -> str:
        ahora = int(time.time())
        expiracion = ahora + (60 * 60 * 2)  # 2 horas

        payload = {
            # Estándar JWT
            "aud": "jitsi",
            "iss": "chat",
            "iat": ahora,
            "exp": expiracion,
            "nbf": ahora - 5,
            "sub": self._app_id,

            # Contexto Jitsi
            "context": {
                "user": {
                    "name": nombre,
                    "email": correo,
                    "moderator": str(es_moderador).lower(),
                    "id": str(uuid.uuid4()),  # Añadir ID único
                },
                "features": {
                    "recording": str(es_moderador).lower(),
                    "livestreaming": "false",
                    "outbound-call": "false",
                    "transcription": "false",
                },
                "room": f"{self._app_id}/{sala_id}"  # Mover room al contexto
            },
            "moderator": es_moderador,
            "room": f"{self._app_id}/{sala_id}",
            "participant": {
                "name": nombre,
                "email": correo,
                "role": "moderator" if es_moderador else "participant"
            }
        }

        token = jwt.encode(
            payload,
            self._private_key,
            algorithm="RS256",
            headers={"kid": self._api_key_id}
        )
        return token

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
        
        # PASO 1: Crear la sala en el backend de 8x8
        sala_creada = await self._crear_sala_en_8x8(sala_id)
        if not sala_creada:
            logger.warning(f"No se pudo crear la sala {sala_id}, pero intentaremos continuar")
        
        # PASO 2: Generar tokens
        token_alumno = self.generar_token_alumno(sala_id, nombre_alumno, correo_alumno)
        token_moderador = self.generar_token_moderador(sala_id, nombre_profesor)

        # PASO 3: Construir URLs con parámetros adicionales para mejor UX
        link_alumno = (
            f"{self._base_url}/{self._app_id}/{sala_id}"
            f"?jwt={token_alumno}"
            f"&config.knocking=true"  # Forzar "tocar la puerta"
            f"&userInfo.displayName={nombre_alumno}"
        )
        
        link_supervisor = (
            f"{self._base_url}/{self._app_id}/{sala_id}"
            f"?jwt={token_moderador}"
            f"&config.knocking=false"  # Moderador entra directo
            f"&config.prejoinPageEnabled=false"  # Saltar pantalla de pre-unión
            f"&userInfo.displayName={nombre_profesor}"
        )

        logger.info(f"Sala {sala_id} creada. Links generados")

        return LinksSala(
            alumno     = link_alumno,
            supervisor = link_supervisor,
            sala_id    = sala_id
        )

    async def cerrar_sala(self, sala_id: str) -> bool:
        """Opcional: eliminar la sala explícitamente"""
        try:
            api_token = self._generar_token_para_api("DELETE", f"/rooms/{sala_id}")
            
            headers = {
                'Authorization': f'Bearer {api_token}',
            }
            
            url = f"{self._api_base_url}/rooms/{self._app_id}/{sala_id}"
            
            response = requests.delete(url, headers=headers, timeout=10)
            
            if response.status_code in [200, 204]:
                logger.info(f"Sala {sala_id} cerrada exitosamente")
                if sala_id in self._salas_creadas:
                    self._salas_creadas.remove(sala_id)
                return True
            else:
                logger.warning(f"Error cerrando sala {sala_id}: {response.status_code}")
                return False
                
        except Exception as e:
            logger.exception(f"Excepción cerrando sala {sala_id}")
            return False