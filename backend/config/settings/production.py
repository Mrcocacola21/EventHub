from .base import *

DEBUG = False

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Enable when HTTPS termination is configured at the proxy/Nginx layer.
# SECURE_SSL_REDIRECT = True

