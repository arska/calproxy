from flask import Flask, Response, request, abort
import os
import requests
from werkzeug.contrib.cache import FileSystemCache
cache = FileSystemCache(cache_dir="cache/")
import time
from prometheus_client import Histogram, Counter, Summary, Gauge, REGISTRY, generate_latest
import threading

app = Flask(__name__)
FLASK_REQUEST_LATENCY = Histogram('flask_request_latency_seconds', 'Flask Request Latency', ['method', 'endpoint'])
FLASK_REQUEST_COUNT = Counter('flask_request_count', 'Flask Request Count', ['method', 'endpoint', 'http_status'])
update_time = Summary('update_seconds', 'Time spent loading data upstream')

@app.route('/metrics')
def metrics():
    return generate_latest(REGISTRY)

@app.route('/', defaults={'path': 'root'})
@app.route('/<path>')
def calproxy(path):
    # check if there is a corresponding env var set, return empty response (without requiring auth) if not
    url = os.environ.get('URL_' + path, False)
    if not url:
        return ''

    auth = request.authorization
    if os.environ.get('AUTHUSER', False) and os.environ.get('AUTHPASS', False):
        # require authentication
        if not auth or not auth.username == os.environ.get('AUTHUSER') or not auth.password == os.environ.get('AUTHPASS'):
            return Response(
                'Could not verify your access level for that URL.\n'
                'You have to login with proper credentials', 401,
                {'WWW-Authenticate': 'Basic realm="Login Required"'}
            )
    # if no auth is required or if proper credentials were provided continue
    print("request: %s" % path)
    data = cache.get(url)
    if data == None:
        #data = update(url)
        print("no data for %s, spawning async update, returning 404" % path)
        async_update(url)
        abort(404)
    age = time.time() - data['time']
    print('data from %d (age %d)' % (data['time'], age))
    if age > os.environ.get('cachetime', 60*60) or age < 0:
        print("old data for %s, spawning async update, returning old data" % path)
        async_update(url)
    resp = Response(data['data'].text)
    resp.headers['Content-Type'] = data['data'].headers['Content-Type']
    return resp

@update_time.time()
def update(url):
    print("starting to load %s"%url)
    r = requests.get(url)
    r.raise_for_status()
    data = {'data': r, 'time': time.time()}
    cache.set(url, data, timeout=0)
    print("done updating %s"%url)
    return data

def async_update(url):
    existingthread = False
    for t in threading.enumerate():
        if t.name == url:
            print("not starting new thread as there is one running already for %s" % url)
            return False
    threading.Thread(target=update,args=(url,),name=url).start()
    print("spawned new thread for %s" % url)

def before_request():
    request.start_time = time.time()

def after_request(response):
    request_latency = max(time.time() - request.start_time, 0) # time can go backwards...
    FLASK_REQUEST_LATENCY.labels(request.method, request.path).observe(request_latency)
    FLASK_REQUEST_COUNT.labels(request.method, request.path, response.status_code).inc()
    return response

if __name__ == "__main__":
    app.before_request(before_request)
    app.after_request(after_request)
    app.run(host='0.0.0.0',port=os.environ.get('listenport', 8080))

