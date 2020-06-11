import socket
from threading import Thread
import sys
from urllib.parse import unquote, unquote_plus

from http.client import responses

import datetime

def _500():
    return 'HTTP/1.1 500 {0}\r\n\r\n {0}\n'.format(responses[500]).encode("utf-8")

def _301(host, path):
    print("{} {}".format(301, r:=responses[301]))
    return 'HTTP/1.1 301 {0}\r\nLocation:http://{1}{2}\r\n\r\n {0}\n'.format(r, host, path[:-1]).encode("utf-8")

def remove_w(l, w=['']):
    return [a for a in l if a not in w]

def make_formdata(others):
    value_dic = {}

    _, post_value = others.split('\r\n\r\n')
    post_value= unquote_plus(post_value)
    
    try:
        for post_v in post_value.split('&'):
            key, value = post_v.split('=', 1)
            value_dic[key]=value
        value_dic['error'] = False
    except:
        value_dic['error'] = True

    return value_dic

def make_formdata_multi(others, val):
    value_dic = {}

    try:
        _, post_value = others.split('\r\n\r\n',1)
        value_dic['formdata'] = post_value
        value_dic['boundary'] = val.split('=')[1]
        value_dic['error'] = False
    except:
        value_dic['error'] = True

    return value_dic

class Saba():
    def __init__(self, app, host = '127.0.0.1', port = 8000):
        self.host = host
        self.port = port
        self.request_queue_size = 50
        self.app = app

    def parse_request(self):
        # Parse rquest

        # (method, path, protocol) : request line / others : request header
        self.method, self.path, others = self.request_data.decode('iso-8859-1').split(' ', 2)
        self.protocol, self.r_host, others = others.split('\r\n', 2)

        self.path = unquote(self.path)

        if '?' in self.path:
            self.path, self.query = self.path.split('?', 1)
            self.path = self.path+'/'
            if self.query[-1] == '/':
                self.query = self.query[:-1]

        else:
            self.query=""

        self.r_host = self.r_host.split(': ')[1]

        value_dic = {}
        if self.method == 'POST':
            for o in remove_w(others.split('\r\n')):
                if len(o := o.split(': '))==2:
                    key, val = o
                    if key=='Content-Type':
                        if 'multipart/form-data' in val:
                            value_dic = make_formdata_multi(others, val)
                        elif val=='application/x-www-form-urlencoded':
                            value_dic = make_formdata(others)

        self.post_value = value_dic

        print('{} {} {}'.format(datetime.datetime.now(), self.method, self.path), end=' ')

    def make_env(self):
        env = {
        'REQUEST_METHOD' : self.method,
        'SCRIPT_NAME' : '',
        'PATH_INFO' : self.path,
        'QUERY_STRING' : self.query,
        'CONTENT_TYPE':'',
        'CONTENT_LENGTH':'',
        'SERVER_NAME': 'saba_server/beta',
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

        'saba_post_value':self.post_value
        }
        return env

    # Return status & env.
    def handle_one_request(self, conn):
        self.request_data = b''
        # Loop until all data is received.
        while True:

            # Receive data(maximum 4096 bytes).
            data = conn.recv(4096)# Blocking

            self.request_data += data

            if (len(data)<4096) or (not data):
                break

        if self.request_data == b'':
            return {'status':'500', 'env':None}

        self.parse_request()

        env = self.make_env()

        if len(self.path.split('/')) == 3 and self.path[-1] == '/':
            return {'status':'301', 'env':env, 'host':self.r_host}

        return {'status':'200', 'env':env}

    def keep_swimming(self):

        # AF_INET : IPv4/ SOCK_STREAM : TCP/IP
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:

            # Set some socket options.
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Specify 'IP address' and 'port'.
            s.bind((self.host, self.port))

            # Wait for connection.
            s.listen(self.request_queue_size)

            while True:
                # When someone comes in, adds the connection and address.
                conn, _ = s.accept()
                dic = self.handle_one_request(conn)

                if dic['env'] is None:
                    continue

                # Create thread.
                thread = Thread(target=swimming, args=(conn, dic, self.app), daemon=True)

                # Start thread.
                thread.start()

#Loop handler.
def swimming(conn, dic, app):
    env = dic['env']

    # Opne the conection.
    with conn:
        if dic['status']=='301':
            response_data = _301(dic['host'], env['PATH_INFO'])
        else:
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
        print(s)

    response_data = app(env, start_response)

    if response_data is None:
        response_data=b''
        content_length=0
    else:
        content_length=len(response_data)

    status_line = "HTTP/1.1 {}".format(status_code).encode("utf-8")

    if len(headers)==0 or status_code is None:
        return _500()
    else:
        headers = [f"{k}: {v}" for k, v in headers]
        headers.append('CONTENT_LENGTH: {}'.format(content_length))
        headers = '\r\n'.join(headers).encode('utf-8')
        response_data=status_line+b'\r\n'+headers+b'\r\n\r\n'+response_data[0]

    return response_data