# the base file and class for all controllers to inherit from

# standard library
import json
import logging

# app engine imports
from google.appengine.api import users, memcache
import webapp2

# local
from gae_blog.config import TEMPLATES_PATH, BLOG_PATH
from gae_blog import model

# see if caching is available
try:
    from gae_html import cacheHTML, renderIfCached
except ImportError:
    def cacheHTML(controller, function, **kwargs):
        return function()
    def renderIfCached(action):
        def decorate(*args,  **kwargs):
            return action(*args, **kwargs)
        return decorate

# see if asset management is available
try:
    from gae_deploy import static
except ImportError:
    def static(url):
        return url

# we have to force the use of the local Mako folder rather than the system one
# this is a problem with how Mako does imports (assumes an installed package)
# also, this would never happen on production as Google blocks these things
import os
if os.environ.get('SERVER_SOFTWARE', '').startswith('Development'):
    import sys
    paths_to_remove = []
    for path in sys.path:
        if 'mako' in path.lower() or 'dist-packages' in path:
            paths_to_remove.append(path)
    for path in paths_to_remove:
        sys.path.remove(path)
    sys.path.append(BLOG_PATH)

from mako.lookup import TemplateLookup


class BaseController(webapp2.RequestHandler):

    template_lookup = TemplateLookup(directories=[TEMPLATES_PATH], input_encoding='utf-8')

    def cacheAndRenderTemplate(self, filename, **kwargs):
        def renderHTML():
            return self.compileTemplate(filename, **kwargs)
        if "errors" in kwargs or self.isUserAdmin():
            html = renderHTML()
        else:
            html = cacheHTML(self, renderHTML, **kwargs)
        return self.response.out.write(html)

    def compileTemplate(self, filename, **kwargs):
        template = self.template_lookup.get_template(filename)
        # add some standard variables
        kwargs["blog_url"] = self.blog_url
        blog = self.getBlog()
        kwargs["blog"] = blog
        user = self.getUser()
        kwargs["user"] = user
        if user:
            kwargs["user_is_admin"] = self.isUserAdmin()
        kwargs["static"] = static
        return template.render_unicode(**kwargs)

    def renderTemplate(self, filename, **kwargs):
        self.response.out.write(self.compileTemplate(filename, **kwargs))

    def renderError(self, status_int):
        self.response.set_status(status_int)
        error_message = "Error " + str(status_int) + ": " + self.response.http_status_message(status_int)
        self.renderTemplate("error.html", error_message=error_message)

    def renderJSON(self, data):
        self.response.headers['Content-Type'] = "application/json"
        self.response.out.write(json.dumps(data, ensure_ascii=False, encoding='utf-8'))

    # this overrides the base class for handling things like 500 errors
    def handle_exception(self, exception, debug):
        # log the error
        logging.exception(exception)

        # if this is development, then print out a stack trace
        if os.environ.get('SERVER_SOFTWARE', '').startswith('Development'):
            super(BaseController, self).handle_exception(exception, True)
            return

        # if the exception is a HTTPException, use its error code
        # otherwise use a generic 500 error code
        if isinstance(exception, webapp2.HTTPException):
            status_int = exception.code
        else:
            status_int = 500

        self.renderError(status_int)

    def getUser(self):
        return users.get_current_user()

    def isUserAdmin(self):
        return users.is_current_user_admin()

    def getBlog(self):
        return model.Blog.get_by_key_name(self.blog_slug)

    def getSession(self):
        """ returns dictionary-like object for storing data across requests """
        value = {}
        # look for a session id in the cookies
        sid = self.request.cookies.get("sid")
        if sid:
            value = memcache.get(sid)
            if value is None: value = {}
        return value

    def saveSession(self, session):
        # look for a session id in the cookies
        sid = self.request.cookies.get("sid")
        # if it's not there, generate one and set it
        if not sid:
            sid = ''.join('%02x' % ord(x) for x in os.urandom(16))
            self.response.headers.add_header('Set-Cookie', 'sid=' + sid + '; Path=/;')
        # save the session to memcache under that id
        memcache.set(sid, session)

    # helper functions for validating
    def validate(self, validator, value):
        try:
            value = validator.to_python(value)
        except:
            value = None
        return value

    def errorsToSession(self, form_data, errors):
        session = self.getSession()
        session["form_data"] = form_data
        session["errors"] = errors
        self.saveSession(session)

    def errorsFromSession(self):
        session = self.getSession()
        form_data = {}
        if "form_data" in session:
            form_data = session["form_data"]
            del session["form_data"]
        errors = {}
        if "errors" in session:
            errors = session["errors"]
            del session["errors"]
        if form_data or errors:
            self.saveSession(session)
        return form_data, errors

    @property
    def blog_slug(self):
        return self.request.path.split('/')[1] # we add the slash for easy URL making

    @property
    def blog_url(self):
        return '/' + self.blog_slug


# decorators
def renderIfCachedNoErrors(action):
    def decorate(*args,  **kwargs):
        controller = args[0]
        session = controller.getSession()
        if "errors" in session or controller.isUserAdmin():
            return action(*args, **kwargs)
        else:
            return renderIfCached(action)(*args, **kwargs)
    return decorate
