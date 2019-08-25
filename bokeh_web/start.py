import sys

from tornado.ioloop import IOLoop
from bokeh.server.server import Server
from bokeh.application import Application
from bokeh.application.handlers.directory import DirectoryHandler


try:
    model_url = sys.argv[1]
    model_path = sys.argv[2]
    port = sys.argv[3]
except:
    pass


io_loop = IOLoop.current()

server = Server(applications={'/bokeh_web': Application(DirectoryHandler(filename='.', argv=[model_url, model_path]))},
                io_loop=io_loop,
                port=int(port),
                index=".",
                allow_websocket_origin=['*'])

server.start()
#server.show('/bokeh_web')
io_loop.start()
