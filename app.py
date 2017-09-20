from flask import Flask, Response, request
import os
import requests
app = Flask(__name__)

@app.route("/")
def calproxy():
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
    r = requests.get(os.environ.get('URL'))
    return r.text

if __name__ == "__main__":
    app.run(host='0.0.0.0',port=8080)
