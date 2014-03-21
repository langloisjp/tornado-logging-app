import unittest
import tornadoutil
import tornado.testing
import time

class MyService(tornadoutil.LoggingApplication):
    def __init__(self):
        super(MyService, self).__init__('myservice', [(r"/", MyHandler)])

class MyHandler(tornadoutil.RequestHandler):
    def get(self):
        self.timeit('metric', time.sleep, 0.1)
        self.logvalue('caller', self.caller())
        self.require_json_content_type()
        self.set_headers({'X-Request-Id': self.request_id})
        self.set_status(201)
        self.write(self.json({'url': self.appurl()}))

    def post(self):
        self.set_status(300)
        self.write_error(300)


class MyHTTPTest(tornado.testing.AsyncHTTPTestCase):
    def get_app(self):
        return MyService()

    def test_homepage(self):
        response = self.fetch('/', headers={'content-type': 'application/json'})
        self.assertEquals(response.code, 201)
        self.assertIn('url', response.body)

    def test_bad_content_type(self):
        response = self.fetch('/')
        self.assertEquals(response.code, 400)
        self.assertIn('Content type must be application/json', response.body)

    def test_post(self):
        response = self.fetch('/', method='POST', body='test')
        self.assertEquals(response.code, 300)
