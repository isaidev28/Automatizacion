class IAException(Exception):
    """Base de excepciones de la IA"""
    pass

class LLMNoDisponibleException(IAException):
    pass

class TTSNoDisponibleException(IAException):
    pass

class STTNoDisponibleException(IAException):
    pass

class ContextoExcedidoException(IAException):
    """El PDF es demasiado largo para el contexto del LLM"""
    pass