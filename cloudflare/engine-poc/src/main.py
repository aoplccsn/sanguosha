from urllib.parse import urlparse
from workers import Response, WorkerEntrypoint
from sanguosha.session import GameSession
class Default(WorkerEntrypoint):
    async def fetch(self, request):
        if urlparse(request.url).path == "/engine/military":
            session = GameSession.new_game(seed=6, military=True, five_generals=True)
            return Response.json({"cards": len(session.state.cards), "players": len(session.state.players), "ruleset": session.state.ruleset_id})
        return Response("engine-poc")
