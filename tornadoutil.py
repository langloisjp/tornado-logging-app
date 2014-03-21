"""
Tornado server utilities

- LoggingApplication: a base Application class with logging and metrics
- RequestHandler: a base request handler with helpers

Dependencies:
- metrics
- servicelog

See tests/test_tornadoutil.py for usage example.

"""

import json
import datetime
import uuid
import httplib # for httplib.responses

import tornado.web
import tornado.options
import tornado.httpserver
import metrics
import servicelog


REQUEST_ID_HEADER = 'X-Request-Id'
AUTH_USER_HEADER = 'X-Auth-User'


class LoggingApplication(tornado.web.Application):
    """
    Overrides base log_request method to log requests to JSON
    UDP collector. Logs method, uri, remote_ip, etc.

    Also supports logging arbitrary key/value pair logging via a handler's
    'logvalues' attribute.

    >>> app = LoggingApplication('myservice')
    """
    def __init__(self, service_id, *args, **kwargs):
        self.service_id = service_id or 'undefined'
        metrics.configure(prefix=self.service_id)
        super(LoggingApplication, self).__init__(*args, **kwargs)

    def run(self, port): # pragma: no coverage
        """
        Run on given port. Parse standard options and start the http server.
        """
        tornado.options.parse_command_line()
        http_server = tornado.httpserver.HTTPServer(self)
        http_server.listen(port)
        tornado.ioloop.IOLoop.instance().start()

    def log_request(self, handler):
        """
        Override base method to log requests to JSON UDP collector and emit
        a metric.
        """
        packet = {'method': handler.request.method,
                  'uri': handler.request.uri,
                  'remote_ip': handler.request.remote_ip,
                  'status': handler.get_status(),
                  'request_time_ms': handler.request.request_time() * 1000.0,
                  'service_id': self.service_id,
                  'request_id': handler.request.headers.get(REQUEST_ID_HEADER,
                                                            'undefined')
                  }

        # handler can optionally define additional data to log
        if hasattr(handler, 'logvalues'):
            for key, value in handler.logvalues.iteritems():
                packet[key] = value

        servicelog.log(packet)

        metric = "requests." + str(handler.get_status())
        metrics.timing(metric, handler.request.request_time() * 1000.0)

        super(LoggingApplication, self).log_request(handler)


class RequestHandler(tornado.web.RequestHandler):
    """A handler with helpers"""

    def appurl(self):
        """Return URL for app"""
        return self.request.protocol + "://" + self.request.host

    def caller(self):
        """Returns caller's ID (from X-Auth-User)"""
        return self.request.headers.get(AUTH_USER_HEADER, 'undefined')

    def logvalue(self, key, value):
        """Add log entry to request log info"""
        if not hasattr(self, 'logvalues'):
            self.logvalues = {}
        self.logvalues[key] = value

    def halt(self, code, msg=None):
        """Halt processing. Raise HTTP error with given code and message."""
        raise tornado.web.HTTPError(code, msg)

    def json(self, obj):
        """Use our own encoder to support additional types"""
        return json.dumps(obj, cls=JSONEncoder)

    def write_error(self, status_code, **kwargs):
        """Log halt_reason in service log and output error page"""
        message = default_message = httplib.responses.get(status_code, '')
        # HTTPError exceptions may have a log_message attribute
        if 'exc_info' in kwargs:
            (_, exc, _) = kwargs['exc_info']
            if hasattr(exc, 'log_message'):
                message = str(exc.log_message) or default_message
        self.logvalue('halt_reason', message)
        title = "{}: {}".format(status_code, default_message)
        body = "{}: {}".format(status_code, message)
        self.finish("<html><title>" + title + "</title>"
                    "<body>" + body + "</body></html>")

    def timeit(self, metric, func, *args, **kwargs):
        """Time execution of callable and emit metric then return result."""
        return metrics.timeit(metric, func, *args, **kwargs)

    def require_json_content_type(self):
        """Raise 400 error if content type is not json"""
        self.require_content_type('application/json')

    def require_content_type(self, content_type):
        """Raises a 400 if request content type is not as specified."""
        if self.request.headers.get('content-type', '') != content_type:
            self.halt(400, 'Content type must be ' + content_type)

    def prepare(self):
        """Override base method to add a request ID header if needed"""
        self._ensure_request_id_header()

    @property
    def request_id(self):
        """Return request ID from header"""
        return self.request.headers.get(REQUEST_ID_HEADER, 'undefined')

    def set_headers(self, headers):
        """Set headers"""
        for (header, value) in headers.iteritems():
            self.set_header(header, value)

    def _ensure_request_id_header(self):
        "Ensure request headers have a request ID. Set one if needed."
        if REQUEST_ID_HEADER not in self.request.headers:
            self.request.headers.add(REQUEST_ID_HEADER, uuid.uuid1().hex)



class JSONEncoder(json.JSONEncoder):
    """
    Adds support for datetime.datetime objects.

    >>> json.dumps({'a': datetime.datetime(2013, 12, 10)}, cls=JSONEncoder)
    '{"a": "2013-12-10T00:00:00Z"}'
    >>> json.dumps({'a': datetime.time()}, cls=JSONEncoder)
    Traceback (most recent call last):
        ...
    TypeError: datetime.time(0, 0) is not JSON serializable
    """
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            return json.JSONEncoder.default(self, obj)


