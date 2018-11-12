"""
Caching http proxy
"""

import logging
import os
import time
import threading
import requests
from werkzeug.contrib.cache import FileSystemCache
from flask import Flask, Response, request, abort
from prometheus_client import Histogram, Counter, Gauge, Summary
from prometheus_client import generate_latest, REGISTRY
from dotenv import load_dotenv

APP = Flask(__name__)  # Standard Flask app
CACHE = FileSystemCache(cache_dir="cache/")

FLASK_REQUEST_LATENCY = Histogram(
    "flask_request_latency_seconds",
    "Flask Request Latency",
    ["method", "endpoint"],
)

FLASK_REQUEST_COUNT = Counter(
    "flask_request_count",
    "Flask Request Count",
    ["method", "endpoint", "http_status"],
)

FLASK_REQUEST_SIZE = Gauge(
    "flask_request_size_bytes",
    "Flask Response Size",
    ["method", "endpoint", "http_status"],
)


UPDATE_TIME = Summary(
    "update_seconds", "Time spent loading data upstream", None
)

LOGFORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.DEBUG, format=LOGFORMAT)


@APP.route("/metrics")
def metrics():
    """
    Route returning metrics to prometheus
    """
    return generate_latest(REGISTRY)


@APP.route("/health")
def health():
    """
    Kubernetes/OpenShift health check endpoint, abused for cache warming cron
    """
    for envvar in os.environ:
        if envvar.startswith("URL_"):
            url = os.environ.get(envvar)
            cache_update(url)
    return "OK"


@APP.route("/", defaults={"path": "root"})
@APP.route("/<path>")
def calproxy(path):
    """
    Proxy URL as defined in ENV vars
    """
    # check if there is a corresponding env var set,
    # return empty response (without requiring auth) if not
    url = os.environ.get("URL_" + path, False)
    if not url:
        return ""

    auth = request.authorization
    if os.environ.get("AUTHUSER", False) and os.environ.get("AUTHPASS", False):
        # require authentication
        if (
            not auth
            or not auth.username == os.environ.get("AUTHUSER")
            or not auth.password == os.environ.get("AUTHPASS")
        ):
            return Response(
                "Could not verify your access level for that URL.\n"
                "You have to login with proper credentials",
                401,
                {"WWW-Authenticate": 'Basic realm="Login Required"'},
            )
    # if no auth is required or if proper credentials were provided continue
    logging.debug("request: %s", path)
    data = cache_update(url)
    if data is None:
        logging.debug("no data for %s, returning 504 until fetched", url)
        abort(504)
    resp = Response(data["data"].text)
    contenttype = data["data"].headers.get("Content-Type", None)
    if contenttype is not None:
        resp.headers["Content-Type"] = contenttype
    return resp


def cache_update(url, asynchronously=True):
    """
    Update a cache entry, optionally async (new thread)
    """
    data = CACHE.get(url)
    if data is None:
        if asynchronously:
            logging.debug("no data for %s, spawning async update", url)
            async_update(url)
            return None
        data = update(url)
    age = time.time() - data["time"]
    logging.debug("data for %s from %d (age %d)", url, data["time"], age)
    if age > os.environ.get("cachetime", 60 * 60) or age < 0:
        logging.debug("old data for %s, returning stale data", url)
        async_update(url)
    return data


@UPDATE_TIME.time()
def update(url):
    """
    Load proxied URL data into cache
    """
    logging.debug("starting to load %s", url)
    req = requests.get(url)
    req.raise_for_status()
    data = {"data": req, "time": time.time(), "url": url}
    CACHE.set(url, data, timeout=0)
    logging.debug("done updating %s", url)
    return data


def async_update(url):
    """
    Start update in new thread
    """
    for thread in threading.enumerate():
        if thread.name == url:
            logging.debug("not starting new thread for %s", url)
            return False
    threading.Thread(target=update, args=(url,), name=url).start()
    logging.debug("spawned new thread for %s", url)
    return True


def before_request():
    """
    annotate the processing start time to each flask request
    """
    request.start_time = time.time()


def after_request(response):
    """
    after returning the request calculate metrics about this request
    """
    # time can go backwards...
    request_latency = max(time.time() - request.start_time, 0)
    # pylint: disable-msg=no-member
    FLASK_REQUEST_LATENCY.labels(request.method, request.path).observe(
        request_latency
    )
    FLASK_REQUEST_SIZE.labels(
        request.method, request.path, response.status_code
    ).set(len(response.data))
    FLASK_REQUEST_COUNT.labels(
        request.method, request.path, response.status_code
    ).inc()
    return response


if __name__ == "__main__":
    load_dotenv()
    APP.before_request(before_request)
    APP.after_request(after_request)
    APP.run(host="0.0.0.0", port=os.environ.get("listenport", 8080))
