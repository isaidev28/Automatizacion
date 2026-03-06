from flask import request, jsonify
from flask_restx import Namespace, Resource, fields
from config.dependencies import (
    get_crear_clase_use_case,
    get_gestionar_duda_use_case,
    get_controlar_sala_use_case,
    get_finalizar_clase_use_case
)
from src.application.dtos.crear_clase_dto import CrearClaseDTO
from src.application.dtos.gestionar_duda_dto import GestionarDudaDTO, OrigenIntervencion
from src.application.dtos.controlar_sala_dto import ControlarSalaDTO
import asyncio
import nest_asyncio

nest_asyncio.apply()

ns = Namespace('clases', description='Operaciones de clases IA')


def run_async(coro):
    """Helper para ejecutar coroutines en Flask sin cerrar el event loop"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ========================
# Modelos Swagger
# ========================

modelo_crear_clase = ns.model('CrearClase', {
    'nombre_profesor': fields.String(required=True, example='Dr. García'),
    'nombre_alumno':   fields.String(required=True, example='Juan Pérez'),
    'correo_profesor': fields.String(required=True, example='profesor@email.com'),
    'correo_alumno':   fields.String(required=True, example='alumno@email.com'),
    'url_pdf':         fields.String(required=True, example='https://mentorpdf.s3.amazonaws.com/pdfs/clase.pdf'),
})

modelo_respuesta_clase = ns.model('RespuestaClase', {
    'clase_id':        fields.String,
    'link_alumno':     fields.String,
    'link_supervisor': fields.String,
    'estado':          fields.String,
    'mensaje':         fields.String,
})

modelo_gestionar_duda = ns.model('GestionarDuda', {
    'pregunta': fields.String(required=True, example='¿Qué es el tipado dinámico?'),
    'origen':   fields.String(required=True, example='chat', enum=['chat', 'microfono']),
})

modelo_controlar_sala = ns.model('ControlarSala', {
    'accion': fields.String(required=True, example='pausar', enum=['pausar', 'reanudar', 'finalizar']),
})


# ========================
# Endpoints
# ========================

@ns.route('/')
class CrearClaseResource(Resource):

    @ns.expect(modelo_crear_clase)
    @ns.marshal_with(modelo_respuesta_clase, code=201)
    @ns.doc(description='Crea una nueva clase con IA como profesor')
    def post(self):
        """Crear una nueva clase"""
        datos = request.json
        try:
            dto = CrearClaseDTO(
                nombre_profesor = datos.get('nombre_profesor'),
                nombre_alumno   = datos.get('nombre_alumno'),
                correo_profesor = datos.get('correo_profesor'),
                correo_alumno   = datos.get('correo_alumno'),
                url_pdf         = datos.get('url_pdf'),
            )
            use_case  = get_crear_clase_use_case()
            resultado = run_async(use_case.ejecutar(dto))      # ← run_async

            return {
                'clase_id':        resultado.clase_id,
                'link_alumno':     resultado.link_alumno,
                'link_supervisor': resultado.link_supervisor,
                'estado':          resultado.estado,
                'mensaje':         resultado.mensaje,
            }, 201

        except ValueError as e:
            ns.abort(400, str(e))
        except Exception as e:
            ns.abort(500, f"Error interno: {str(e)}")


@ns.route('/<string:clase_id>/duda')
class GestionarDudaResource(Resource):

    @ns.expect(modelo_gestionar_duda)
    @ns.doc(description='El alumno envía una duda por chat o micrófono')
    def post(self, clase_id):
        """Gestionar duda del alumno"""
        datos = request.json
        try:
            dto = GestionarDudaDTO(
                clase_id = clase_id,
                pregunta = datos.get('pregunta'),
                origen   = OrigenIntervencion(datos.get('origen', 'chat'))
            )
            use_case  = get_gestionar_duda_use_case()
            resultado = run_async(                             # ← run_async
                use_case.ejecutar(clase_id, dto.pregunta, dto.origen.value)
            )
            return {
                'clase_id':        resultado.clase_id,
                'respuesta':       resultado.respuesta,
                'dentro_del_tema': resultado.dentro_del_tema,
                'estado_clase':    resultado.estado_clase,
            }, 200

        except ValueError as e:
            ns.abort(400, str(e))
        except Exception as e:
            ns.abort(500, f"Error interno: {str(e)}")


@ns.route('/<string:clase_id>/controlar')
class ControlarSalaResource(Resource):

    @ns.expect(modelo_controlar_sala)
    @ns.doc(description='Controla el estado de la IA en la sala')
    def post(self, clase_id):
        """Pausar, reanudar o finalizar la clase"""
        datos  = request.json
        accion = datos.get('accion')
        try:
            use_case = get_controlar_sala_use_case()

            if accion == 'pausar':
                run_async(use_case.pausar_ia(clase_id))        # ← run_async
            elif accion == 'reanudar':
                run_async(use_case.reanudar_ia(clase_id))      # ← run_async
            elif accion == 'finalizar':
                run_async(use_case.finalizar_clase(clase_id))  # ← run_async
            else:
                ns.abort(400, f"Acción no válida: {accion}")

            return {'clase_id': clase_id, 'accion': accion, 'status': 'ok'}, 200

        except ValueError as e:
            ns.abort(400, str(e))
        except Exception as e:
            ns.abort(500, f"Error interno: {str(e)}")


@ns.route('/<string:clase_id>')
class ClaseResource(Resource):

    @ns.doc(description='Obtiene el estado actual de una clase')
    def get(self, clase_id):
        """Obtener estado de la clase"""
        try:
            cache  = get_crear_clase_use_case()._cache
            sesion = run_async(cache.obtener_sesion(clase_id)) # ← run_async

            if not sesion:
                ns.abort(404, f"Clase {clase_id} no encontrada")

            return sesion, 200

        except Exception as e:
            ns.abort(500, f"Error interno: {str(e)}")


@ns.route('/<string:clase_id>/finalizar')
class FinalizarClaseResource(Resource):

    @ns.doc(description='Finaliza la clase y libera recursos')
    def delete(self, clase_id):
        """Finalizar clase"""
        try:
            use_case  = get_finalizar_clase_use_case()
            resultado = run_async(use_case.ejecutar(clase_id)) # ← run_async
            return resultado, 200
        except Exception as e:
            ns.abort(500, f"Error interno: {str(e)}")