import socket
from threading import Thread

from http.client import responses

import sys

def _501():
    return 'HTTP/1.1 501 {0}\r\n\r\n {0}\n'.format(responses[501]).encode("utf-8")

def _301(host, path):
    return 'HTTP/1.1 301 {0}\r\nLocation:http://{1}{2}\r\n\r\n {0}\n'.format(responses[301], host, path[:-1]).encode("utf-8")

class Saba():
    def __init__(self, app, host = '127.0.0.1', port = 8000):
        self.host = host
        self.port = port
        self.request_queue_size = 50
        self.app = app

        # AF_INET : IPv4/ SOCK_STREAM : TCP/IP
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Set some socket options.
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Specify 'IP address' and 'port'.
        self.s.bind((self.host, self.port))

        # Wait for connection.
        self.s.listen(self.request_queue_size)

    def parse_request(self):
        # Parse rquest

        # (method, path, protocol) : request line / others : request header
        self.method, self.path, others = self.request_data.decode('iso-8859-1').split(' ', 2)
        self.protocol, self.r_host, _ = others.split('\r\n', 2)

        if self.path in '?':
            self.path, self.query = self.path.split('?', 1)
        else:
            self.query=""

        self.r_host = self.r_host.split(': ')[1]

    def make_env(self):
        env = {
        'REQUEST_METHOD' : self.method,
        'SCRIPT_NAME' : '',
        'PATH_INFO' : self.path,
        'QUERY_STRING' : self.query,
        'CONTENT_TYPE':'',
        'CONTENT_LENGTH':'',
        'SERVER_NAME': socket.getfqdn(),
        'SERVER_PORT': self.port,
        'SERVER_PROTOCOL':self.protocol,
        #HTTP_ Variables

        'wsgi.version':(1,0),
        'wsgi.url_scheme': "http",#https
        'wsgi.input':self.request_data,
        'wsgi.errors':sys.stderr,
        'wsgi.multithread': True,
        'wsgi.multiprocess': False,
        'wsgi.run_once': False,
        }
        return env

    # Return status & env.
    def handle_one_request(self):
        self.request_data = b''
        # Loop until all data is received.
        while True:

            # Receive data(maximum 4096 bytes).
            data = self.conn.recv(4096)# Blocking

            self.request_data += data

            if (len(data)<4096) or (not data):
                break

        if self.request_data == b'':
            return {'status':'501', 'env':None}

        self.parse_request()

        env = self.make_env()

        if len(self.path.split('/')) == 3 and self.path[-1] == '/':
            return {'status':'301', 'env':env, 'host':self.r_host}

        return {'status':'200', 'env':env}

    def keep_swimming(self):
        s = self.s
        while True:
            # When someone comes in, adds the connection and address.
            self.conn, _ = s.accept()
            dic = self.handle_one_request()

            if dic['env'] is None:
                continue

            # Create thread.
            thread = Thread(target=swimming, args=(self.conn, dic, self.app), daemon=True)

            # Start thread.
            thread.start()

#Loop handler.
def swimming(conn, dic, app):
    env = dic['env']

    # Opne the conection.
    with conn:
        response_data = make_responce(env, app)

        if dic['status']=='301':
            response_data = _301(dic['host'], env['PATH_INFO'])

        conn.sendall(response_data)

# Make responce.
def make_responce(env, app):

    headers = []
    status_code = None

    def start_response(s, h, exc_info=None):
        nonlocal headers, status_code
        status_code = s
        headers = h

    response_data = app(env, start_response)

    if response_data is None:
        response_data=b''
        content_length=0
    else:
        content_length=len(response_data)

    status_line = "HTTP/1.1 {}".format(status_code).encode("utf-8")

    if len(headers)==0 or status_code is None:
        return _501()
    else:
        headers = [f"{k}: {v}" for k, v in headers]
        headers.append('CONTENT_LENGTH: {}'.format(content_length))
        headers = '\r\n'.join(headers).encode('utf-8')
        response_data=status_line+b'\r\n'+headers+b'\r\n\r\n'+response_data[0]

    return response_data