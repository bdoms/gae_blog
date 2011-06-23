# this is the main entry point for the application

import os
import sys
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PARENT_DIR not in sys.path:
    sys.path.append(PARENT_DIR)

from google.appengine.ext import webapp
from google.appengine.ext.webapp import util

from gae_blog.config import ROUTES

def main():
    app = application()
    util.run_wsgi_app(app)

def application():
    return webapp.WSGIApplication(ROUTES, debug=True)

if __name__ == "__main__":
    main()
