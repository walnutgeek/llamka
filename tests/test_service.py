import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any

import pytest
import tornado
from typing_extensions import override

from botglue.service import BIND_ERRNO, App, AppService, AppState, PortSeekStrategy, get_json


class OkService(AppService[AppState]):
    """A service that returns ok"""

    def __init__(self):
        super().__init__()

        class WorkerStatusHandler(tornado.web.RequestHandler):
            @override
            def get(self):
                self.write(json.dumps({"ok": True}))

        self.add_route(r"/status", WorkerStatusHandler)


class CheckOkService(AppService[AppState]):
    """A service that checks if the ok service is ok"""

    def __init__(self, *tasks: Callable[[], Any]):
        super().__init__()
        self_service = self
        for i, task in enumerate(tasks):
            self.add_periodic(i + 1, task)

        class CheckOkHandler(tornado.web.RequestHandler):
            @override
            async def get(self):
                u = "http://localhost:8000/status"
                status = await get_json(u)
                self.write(
                    json.dumps(
                        {
                            "my_port": self_service.app.app_states[1].port,  # pyright: ignore [reportOptionalMemberAccess]
                            "status": {"url": u, "ok": status["ok"]},
                            "app_running": self_service.app.is_running,  # pyright: ignore [reportOptionalMemberAccess]
                        }
                    )
                )

        self.add_route(r"/check_ok", CheckOkHandler)


class TerminateAppTask:
    app: App
    timeout: int
    task: asyncio.Task[Any] | None

    def __init__(self, app: App, timeout: int):
        self.app = app
        self.timeout = timeout
        self.task = None

    async def terminate_app(self):
        try:
            await asyncio.sleep(self.timeout)
            self.app.shutdown()
        except asyncio.CancelledError:
            pass

    def __enter__(self):
        self.task = asyncio.create_task(self.terminate_app())  # pyright: ignore [reportUninitializedInstanceVariable]
        return self

    def __exit__(self, exc_type, exc_value, traceback):  # pyright: ignore [reportUnknownParameterType,reportMissingParameterType]
        if self.task and not self.task.done():
            self.task.cancel()


@pytest.mark.asyncio
async def test_ok_service():
    app = App("test", AppState(OkService(), port=8000))

    with TerminateAppTask(app, 5):

        class TestItTask:
            ok: bool | None

            def __init__(self):
                self.ok = None

            async def test_it(self):
                self.status = await get_json("http://localhost:8000/status")  # pyright: ignore [reportUninitializedInstanceVariable,reportUnannotatedClassAttribute]
                self.ports = [st.port for st in app.app_states]  # pyright: ignore [reportUninitializedInstanceVariable,reportUnannotatedClassAttribute]
                self.check_ok = await get_json(f"http://localhost:{self.ports[1]}/check_ok")  # pyright: ignore [reportUninitializedInstanceVariable,reportUnannotatedClassAttribute]

            def test_ok(self):
                if hasattr(self, "check_ok"):
                    assert self.status["ok"]
                    assert self.check_ok["my_port"] == self.ports[1]
                    self.ok = True
                    app.shutdown()

        t = TestItTask()

        app.app_states.append(AppState(CheckOkService(t.test_it, t.test_ok)))
        await app.run()
        print(t.status, t.ports, t.check_ok)
        assert t.ok


@pytest.mark.asyncio
async def test_conflict():
    try:
        app = App("test", AppState(OkService(), port=8075))
        app.app_states.append(
            AppState(CheckOkService(), port=8075, port_seek=PortSeekStrategy.BAILOUT)
        )
        await app.run()
        raise AssertionError
    except OSError as e:
        assert e.errno == BIND_ERRNO


@pytest.mark.asyncio
async def test_sequential(caplog: pytest.LogCaptureFixture):
    caplog.set_level(logging.DEBUG, logger="botglue.service")
    app = App("test", AppState(OkService(), port=8090), AppState(CheckOkService(), port=8090))
    with TerminateAppTask(app, 1):
        await app.run()
        d1 = app.app_states[0].port - 8090  # pyright: ignore [reportOptionalOperand]
        d2 = app.app_states[1].port - app.app_states[0].port  # pyright: ignore [reportOperatorIssue]
        assert d1 >= 0
        assert 0 < d2 < 10
    ports_tried = [
        int(x[1])
        for x in (r.message.split("Trying to listen on port ") for r in caplog.records)
        if len(x) == 2 and x[0] == ""
    ]
    assert len(ports_tried) > 2, f"Too few {ports_tried=}"


@pytest.mark.asyncio
async def test_value_ex():
    try:
        app = App("test", AppState(OkService(), port=8090))
        with TerminateAppTask(app, 1):
            app.app_states.append(AppState(CheckOkService(), port=8090))
            await app.run(max_attempts_to_listen=1)
        raise AssertionError
    except ValueError as e:
        assert e.args == ("Failed to find an available port after max_attempts", 1)
