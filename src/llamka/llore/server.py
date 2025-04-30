import asyncio
import json

import tornado.web
from typing_extensions import override

from llamka.service import App, AppService, AppState


async def check_on_vectorization_sources():
    """Check on vectorization sources"""
    print("Checking on vectorization sources")


class OkService(AppService):
    """A service that returns ok"""

    def __init__(self):
        super().__init__()
        self.add_periodic(5, check_on_vectorization_sources)

        class WorkerStatusHandler(tornado.web.RequestHandler):
            @override
            def get(self):
                self.write(json.dumps({"ok": True}))

        class MainHandler(tornado.web.RequestHandler):
            @override
            def get(self):
                self.write("Welcome to Llore API")

        self.add_route(r"/status", WorkerStatusHandler)
        self.add_route(r"/", MainHandler)


def run_server(port: int = 7532, debug: bool = False):
    """Run the Tornado server"""
    app = App("test", AppState(OkService(), port=port, debug=debug))
    asyncio.run(app.run())


if __name__ == "__main__":
    run_server(debug=True)
