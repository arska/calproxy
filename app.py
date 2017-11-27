from flask import Flask, Response, request
import os
import requests
from werkzeug.contrib.cache import SimpleCache
cache = SimpleCache()

app = Flask(__name__)

@app.route('/', defaults={'path': 'root'})
@app.route('/<path:path>')
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
    data = cache.get(url)
    if data == None:
        r = requests.get(url)
        data = r.text
        cache.set(url, data, timeout=os.environ.get('cachetime', 5*60))
    return data

if __name__ == "__main__":
    app.run(host='0.0.0.0',port=os.environ.get('listenport', 8080))
