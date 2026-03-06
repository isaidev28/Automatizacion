class ClaseException(Exception):
    """Base de todas las excepciones del dominio de clases"""
    pass

class ClaseYaFinalizadaException(ClaseException):
    pass

class AlumnoNoAutorizadoException(ClaseException):
    pass

class PDFInvalidoException(ClaseException):
    pass

class FueraDeTemaException(ClaseException):
    """Se lanza cuando el alumno pregunta algo fuera del contenido del PDF"""
    def __init__(self, pregunta: str):
        self.pregunta = pregunta
        super().__init__(f"Pregunta fuera de tema: {pregunta}")

class SalaNoDisponibleException(ClaseException):
    pass