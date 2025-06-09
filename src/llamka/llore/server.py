import asyncio
import logging
from pathlib import Path

import tornado.web
from typing_extensions import override

from llamka.llore.api import ChatRequest, Models
from llamka.llore.pipeline import Llore
from llamka.periodic import Moment
from llamka.service import App, AppService, AppState, PortSeekStrategy

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class LloreState(AppState):
    llore: Llore

    def __init__(
        self,
        *app_services: AppService,  # pyright: ignore [reportUnknownParameterType, reportMissingTypeArgument]
        port: int | None = None,
        port_seek: PortSeekStrategy | None = None,
        debug: bool = False,
        root: str | Path | None = None,
    ):
        super().__init__(*app_services, port=port, port_seek=port_seek, debug=debug)
        self.llore = Llore(root=root)


class LloreService(AppService[LloreState]):
    """A service that returns ok"""

    def __init__(self):
        super().__init__()
        self.add_periodic(60, self._process_files)
        self.add_periodic(2, lambda: None)  # to make it quit on ctrl-c quickly
        service = self

        class ChatHandler(tornado.web.RequestHandler):
            @override
            async def post(self):
                if service.app_state is None:
                    raise RuntimeError("App state not initialized")
                request = ChatRequest.model_validate_json(self.request.body)
                if request.bot_name is not None:
                    result = await service.app_state.llore.query_bot(
                        request.bot_name, request.messages, llm_name=request.llm_name
                    )
                else:
                    assert request.llm_name is not None
                    result = await service.app_state.llore.query_llm(
                        request.llm_name, request.messages
                    )
                self.write(result.model_dump_json())

        class ModelsHandler(tornado.web.RequestHandler):
            @override
            def get(self):
                if service.app_state is None:
                    raise RuntimeError("App state not initialized")
                models: Models = service.app_state.llore.get_models()
                self.write(models.model_dump_json())

        class MainHandler(tornado.web.RequestHandler):
            @override
            def get(self):
                self.write("Welcome to Llore API")

        self.add_route(r"/chats", ChatHandler)
        self.add_route(r"/models", ModelsHandler)
        self.add_route(r"/", MainHandler)

    def _process_files(self):
        if self.app_state is None:
            raise RuntimeError("App state not initialized")
        moment = Moment.start()
        logger.info("Processing files")
        self.app_state.llore.process_files()
        logger.info(f"Finished processing files: {moment.capture('finished')}")


def run_server(port: int = 7532, debug: bool = False):
    """Run the Tornado server"""
    app = App("llore", LloreState(LloreService(), port=port, debug=debug))
    asyncio.run(app.run())


if __name__ == "__main__":
    run_server(debug=True)
