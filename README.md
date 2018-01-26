# Calproxy

Simple HTTP proxy to proxy a fixed URL per requested path, optionally with HTTP basic auth.

Configuration through environment variables:
- (optional) URL_root: the URL to proxy through for /
- (optional) URL_asdf: the URL to proxy through for /asdf
- (optional) AUTHUSER: username to require for basic auth
- (optional) AUTHPASS: password to require for basic auth
- (optional) listenport: port to listen on, defaults to 8080
- (optional) cachetime: number of seconds to cache responses, defaults to 60*60s=1h

Authentication is only enforced if both AUTHUSER and AUTHPASS are specified

if there is no corresponding URL_path environment variable for a requested path the proxy returns an empty response (without requiring authentication, e.g. for a health check).

When a URL is requested the first time and the cache is empty an update is scheduled to happen in the background and an error (504 gateway timeout) is returned. As soon as the data is in the cache it is returned to requests. After the cachetime has expired each request will schedule an update in the background and old data will be returned until the update has completed. Only one update will run concurrently per target/upstream URL.

The special url /health is used to pre-fetch all URL_xxx.

The project is called calproxy because my use case is to proxy calendar availabilities where the upstream server takes about 2 minutes to export the calendar and the destination system times out after a few seconds.
