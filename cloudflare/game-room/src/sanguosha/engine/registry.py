"""Action type to handler mapping; the engine has no concrete action branches."""

from .actions import Action, ActionHandler
from .errors import UnknownActionHandler


class ActionHandlerRegistry:
    def __init__(self) -> None:
        self._handlers: dict[type[Action], ActionHandler] = {}

    def register(self, action_type: type[Action], handler: ActionHandler) -> None:
        self._handlers[action_type] = handler

    def handler_for(self, action: Action) -> ActionHandler:
        try:
            return self._handlers[type(action)]
        except KeyError as exc:
            raise UnknownActionHandler(f"no handler for {type(action).__name__}") from exc
