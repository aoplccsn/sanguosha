class EngineError(Exception):
    """Base error for resolution protocol violations."""


class InvalidEngineState(EngineError):
    pass


class InvalidDecision(EngineError):
    pass


class UnknownRequest(InvalidDecision):
    pass


class UnknownActionHandler(EngineError):
    pass


class ResolutionError(EngineError):
    pass
