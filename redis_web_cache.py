# -*- coding: utf-8 -*-

import BaseHTTPServer
import redis
import requests
import sys
import cgi

from SocketServer import ThreadingMixIn


class RedisCacheHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    db = redis.StrictRedis(host='localhost', port=6379, db=0)

    def do_GET(self):
        if self.db.exists(self.path):
            print "Cache hit"
            data = self.db.get(self.path)
            status_code = 200
        else:
            print "Cache miss"
            r = requests.get(self.path)

            data = r.content
            status_code = r.status_code
            cache_control = self.__cache_control(r.headers.get("cache-control"))

            if not cache_control["no-cache"]:
                self.db.set(self.path, data)
                self.db.expire(self.path, cache_control["max-age"])

        self.send_response(status_code)
        self.end_headers()
        self.wfile.writelines(data)

    def do_POST(self):
        query_string = self.rfile.read(int(self.headers['Content-Length']))
        args = dict(cgi.parse_qsl(query_string))
        r = requests.post(self.path, args)
        self.send_response(r.status_code)
        self.end_headers()
        self.wfile.writelines(r.content)

    def __cache_control(self, cache_header):
        """ extract values from cache-control header"""
        # default caching values
        cache_control = {"no-cache": False, "max-age": 300}
        if not cache_header:
            return cache_control

        split_header = cache_header.split(", ")
        for v in split_header:
            if v == 'no-cache':
                cache_control['no-cache'] = True
            elif "max-age" in v:
                cache_control['max-age'] = v.split("=")[1]

        return cache_control


class ThreadedHTTPServer(ThreadingMixIn, BaseHTTPServer.HTTPServer):
    """Handle requests in a separate thread."""


def run(args):
    if len(args) != 2:
        print "Usage: redis_web_cache.py HOST PORT"
        exit()

    host = args[0]
    port = int(args[1])
    server_address = (host, port)
    httpd = ThreadedHTTPServer(server_address, RedisCacheHandler)
    print "start redis cache server:", "%s:%d" % (host, port)
    print "use <Ctrl-C> to stop"
    httpd.serve_forever()

if __name__ == '__main__':
    run(sys.argv[1::])
