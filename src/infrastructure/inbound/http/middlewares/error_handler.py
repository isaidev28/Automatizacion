from flask import jsonify
from src.domain.exceptions.clase_exception import (
    ClaseException,
    AlumnoNoAutorizadoException,
    PDFInvalidoException,
    SalaNoDisponibleException
)
from src.domain.exceptions.ia_exception import (
    IAException,
    LLMNoDisponibleException,
    TTSNoDisponibleException
)


def registrar_error_handlers(app):

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({
            "error":   "Bad Request",
            "mensaje": str(e.description)
        }), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({
            "error":   "Not Found",
            "mensaje": str(e.description)
        }), 404

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({
            "error":   "Internal Server Error",
            "mensaje": str(e.description)
        }), 500

    @app.errorhandler(AlumnoNoAutorizadoException)
    def alumno_no_autorizado(e):
        return jsonify({
            "error":   "Forbidden",
            "mensaje": str(e)
        }), 403

    @app.errorhandler(PDFInvalidoException)
    def pdf_invalido(e):
        return jsonify({
            "error":   "PDF Inválido",
            "mensaje": str(e)
        }), 422

    @app.errorhandler(LLMNoDisponibleException)
    def llm_no_disponible(e):
        return jsonify({
            "error":   "Servicio IA no disponible",
            "mensaje": str(e)
        }), 503