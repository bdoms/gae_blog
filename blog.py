# this is the main entry point for the application

from google.appengine.ext import webapp
from google.appengine.ext.webapp import util

from gaeblog.config import ROUTES

def main():
    app = application()
    util.run_wsgi_app(app)

def application():
    return webapp.WSGIApplication(ROUTES, debug=True)

if __name__ == "__main__":
    main()
