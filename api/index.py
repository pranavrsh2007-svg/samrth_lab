import sys
import os

# Ensure the root project directory is on sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the WSGI Flask application instance
from app import app

class VercelPathFixMiddleware:
    """
    Normalizes PATH_INFO when Vercel serverless rewrites route requests to /api/index.
    Ensures that / and subpaths match Flask's route rules instead of causing 404s.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        # Handle cases where Vercel passed /api/index or /api/index/... as path
        if path == '/api/index' or path == '/api/index/':
            environ['PATH_INFO'] = '/'
        elif path.startswith('/api/index/'):
            environ['PATH_INFO'] = path[len('/api/index'):]

        # Support Vercel proxy headers for original path
        orig_uri = environ.get('HTTP_X_NOW_ROUTE_MATCHES') or environ.get('HTTP_X_FORWARDED_PATH')
        if orig_uri and not path.startswith('/static/'):
            if orig_uri.startswith('/'):
                environ['PATH_INFO'] = orig_uri

        return self.wsgi_app(environ, start_response)

app.wsgi_app = VercelPathFixMiddleware(app.wsgi_app)

