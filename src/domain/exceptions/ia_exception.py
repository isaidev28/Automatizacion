class IAException(Exception):
    """Base de la excepciones de la IA"""
    pass

class LLMNoDisponibleExepction(IAException):
    pass

class TTSNoDisponibleException(IAException):
    pass

class STTNoDisponibleException(IAException):
    pass

class ContextoExcedidoException(IAException):
    """El PDF es demasiado largo para el contexto del LLM"""
    pass