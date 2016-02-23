import logging
import json
import os.path
import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.gen
import tornado.options
from concurrent.futures import ThreadPoolExecutor
from tornado.options import define, options

from CetTicket import CetTicket, TicketNotFound

define('address', default='127.0.0.1', help='bind on specific address', type=str)
define('debug', default=False, help='run in debug mode', type=bool)
define('port', default=8000, help='run on the given port', type=int)


class BaseHandler(tornado.web.RequestHandler):
    pass


class IndexHandler(BaseHandler):
    def get(self, *args, **kwargs):
        self.render('index.html')


class ScoreHandler(BaseHandler):
    executor = ThreadPoolExecutor(max_workers=5)

    @tornado.gen.coroutine
    def post(self, *args, **kwargs):
        ticket = self.get_body_argument('ticket', None)
        name = self.get_body_argument('name', None)
        def get_score(ticket, name):
            try:
                return CetTicket.get_score(ticket, name)
            except:
                return dict(error=True)
        result = yield self.executor.submit(get_score, ticket, name)
        self.render('result.html', result=result)


class TicketHandler(BaseHandler):
    executor = ThreadPoolExecutor(max_workers=5)

    @tornado.gen.coroutine
    def post(self, *args, **kwargs):
        province = self.get_body_argument('province', None)
        school = self.get_body_argument('school', None)
        name = self.get_body_argument('name', None)
        cet = int(self.get_body_argument('cet_type', None))

        def find_ticket_number(province, school, name, cet_type):
            result = dict(error=False)
            try:
                result['ticket_number'] = CetTicket.find_ticket_number(province, school, name, cet_type=cet_type)
            except TicketNotFound:
                result['error'] = True
            return result
        
        ticket = yield self.executor.submit(find_ticket_number,
                                            province, school, name, cet_type=cet)
        def get_score(ticket, name):
            try:
                return CetTicket.get_score(ticket, name)
            except:
                return dict(error=True)
        result = yield self.executor.submit(get_score, ticket, name)
        self.render('result.html', result=result)


class Application(tornado.web.Application):
    def __init__(self, debug=True):
        handlers = [
            ('/', IndexHandler),
            ('/score', ScoreHandler),
            ('/ticket', TicketHandler)
        ]
        settings = {
            'template_path': os.path.join(os.path.dirname(__file__), 'templates'),
            'static_path': os.path.join(os.path.dirname(__file__), 'static'),
            'debug': debug
        }
        super(Application, self).__init__(handlers, **settings)


def main():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application(debug=options.debug))
    http_server.listen(options.port, address=options.address)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == '__main__':
    main()
