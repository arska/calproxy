# Calproxy

Very simple HTTP proxy to proxy one fixed URL, optionally with HTTP basic auth.

Configuration through environment variables:
- URL: the URL to proxy through. required - you will only get "500 server error" if left empty
- (optional) AUTHUSER: username to require for basic auth
- (optional) AUTHPASS: password to require for basic auth

Authentication is only enforced if both AUTHUSER and AUTHPASS are specified

The project is called calproxy because my use case is to proxy calendar availabilities.
