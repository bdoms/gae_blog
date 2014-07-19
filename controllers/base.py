# the base file and class for all controllers to inherit from

# standard library
import json
import logging
import os

# app engine api imports
from google.appengine.api import users, memcache

# app engine included libraries imports
import jinja2
import webapp2
from webapp2_extras import sessions

# local
from gae_blog.config import TEMPLATES_PATH
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


class BaseController(webapp2.RequestHandler):

    jinja_env = jinja2.Environment(autoescape=True, loader=jinja2.FileSystemLoader(TEMPLATES_PATH))

    def dispatch(self):
        # get a session store for this request
        self.session_store = sessions.get_store(request=self.request)

        webapp2.RequestHandler.dispatch(self)

        # save all sessions
        self.session_store.save_sessions(self.response)

    @webapp2.cached_property
    def session(self):
        # uses the default cookie key
        return self.session_store.get_session()

    def cacheAndRenderTemplate(self, filename, **kwargs):
        def renderHTML():
            return self.compileTemplate(filename, **kwargs)
        if "errors" in kwargs or self.user_is_admin:
            html = renderHTML()
        else:
            html = cacheHTML(self, renderHTML, **kwargs)
        return self.response.out.write(html)

    def compileTemplate(self, filename, **kwargs):
        template = self.jinja_env.get_template(filename)
        # add some standard variables
        kwargs["blog_url"] = self.blog_url
        kwargs["blog"] = self.blog
        if self.blog and self.blog.template:
            kwargs["blog_base"] = '../../' + self.blog.template
        else:
            kwargs["blog_base"] = 'default_base.html'
        kwargs["user"] = self.user
        if self.user:
            kwargs["user_is_admin"] = self.user_is_admin
        kwargs["static"] = static
        return template.render(kwargs)

    def renderTemplate(self, filename, **kwargs):
        self.response.out.write(self.compileTemplate(filename, **kwargs))

    def renderError(self, status_int, stacktrace=None):
        self.response.set_status(status_int)
        page_title = "Error " + str(status_int) + ": " + self.response.http_status_message(status_int)
        self.renderTemplate("error.html", stacktrace=stacktrace, page_title=page_title)

    def renderJSON(self, data):
        self.response.headers['Content-Type'] = "application/json"
        self.response.out.write(json.dumps(data, ensure_ascii=False, encoding='utf-8'))

    # this overrides the base class for handling things like 500 errors
    def handle_exception(self, exception, debug):
        # log the error
        logging.exception(exception)

        # if this is development, then print out a stack trace
        stacktrace = None
        if os.environ.get('SERVER_SOFTWARE', '').startswith('Development') or self.user_is_admin:
            import traceback
            stacktrace = traceback.format_exc()

        # if the exception is a HTTPException, use its error code
        # otherwise use a generic 500 error code
        if isinstance(exception, webapp2.HTTPException):
            status_int = exception.code
        else:
            status_int = 500

        self.renderError(status_int, stacktrace=stacktrace)

    @webapp2.cached_property
    def user(self):
        return users.get_current_user()

    @webapp2.cached_property
    def user_is_admin(self):
        return users.is_current_user_admin()

    @webapp2.cached_property
    def blog(self):
        return model.Blog.get_by_id(self.blog_slug)

    # helper functions for validating
    def validate(self, validator, value):
        try:
            value = validator.to_python(value)
        except:
            value = None
        return value

    def errorsToSession(self, form_data, errors):
        self.session["form_data"] = form_data
        self.session["errors"] = errors

    def errorsFromSession(self):
        form_data = self.session.pop("form_data", {})
        errors = self.session.pop("errors", {})
        return form_data, errors

    @webapp2.cached_property
    def blog_slug(self):
        return self.request.path.split('/')[1] # we add the slash for easy URL making

    @webapp2.cached_property
    def blog_url(self):
        return '/' + self.blog_slug


# decorators
def renderIfCachedNoErrors(action):
    def decorate(*args,  **kwargs):
        controller = args[0]
        if "errors" in controller.session or controller.user_is_admin:
            return action(*args, **kwargs)
        else:
            return renderIfCached(action)(*args, **kwargs)
    return decorate
