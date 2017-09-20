# Calproxy

Very simple HTTP proxy to proxy a fixed URL per requested path, optionally with HTTP basic auth.

Configuration through environment variables:
- (optional) URL_root: the URL to proxy through for /
- (optional) URL_asdf: the URL to proxy through for /asdf
- (optional) AUTHUSER: username to require for basic auth
- (optional) AUTHPASS: password to require for basic auth

Authentication is only enforced if both AUTHUSER and AUTHPASS are specified

if there is no corresponding URL_path environment variable for a requested path the proxy returns an empty response (without requiring authentication).

The project is called calproxy because my use case is to proxy calendar availabilities.
