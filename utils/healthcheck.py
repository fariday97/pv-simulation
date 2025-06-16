import http.client
import sys

try:
    c = http.client.HTTPConnection('localhost', int(sys.argv[1]))
    c.request('GET', '/health')
    r = c.getresponse()
    sys.exit(0 if r.status == 200 else 1)
except Exception:
    sys.exit(1)
