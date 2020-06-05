import socket
from threading import Thread

import sys

def _501():
    return b'HTTP/1.1 501\r\n\r\n Not Implemented\n'

class Saba():
    def __init__(self, app, host = '127.0.0.1', port = 8000):
        self.host = host
        self.port = port
        self.request_queue_size = 5
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
        self.method, self.path, others = self.request_data.decode('iso-8859-1').split(' ', 2)
        self.protocol , _ = others.split('\r\n', 1)

        if self.path in '?':
            self.path, self.query = self.path.split('?', 1)
        else:
            self.query=""

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
            return None

        self.parse_request()

        env = self.make_env()

        return env

    def keep_swimming(self):
        s = self.s
        while True:
            # When someone comes in, adds the connection and address.
            self.conn, _ = s.accept()
            env = self.handle_one_request()

            if env is None:
                continue

            # Create thread.
            thread = Thread(target=swimming, args=(self.conn, env, self.app), daemon=True)

            # Start thread.
            thread.start()

#Loop handler.
def swimming(conn, env, app):

    # Opne the conection.
    with conn:
        response_data = make_responce(env, app)

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