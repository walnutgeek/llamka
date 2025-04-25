from typing import override

import tornado.ioloop
import tornado.web


class MainHandler(tornado.web.RequestHandler):
    @override
    def get(self):
        self.write("Welcome to Llore API")


def make_app(debug: bool | None = False) -> tornado.web.Application:
    """Create and configure the Tornado application"""
    return tornado.web.Application(
        [
            (r"/", MainHandler),
        ],
        debug=debug,
    )


def run_server(port: int = 7532, debug: bool = False):
    """Run the Tornado server"""
    app = make_app(debug=debug)
    app.listen(port)
    print(f"Server running on port {port}")
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    run_server(debug=True)
