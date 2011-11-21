# the base file and class for all controllers to inherit from

# app engine imports
from google.appengine.ext import webapp
from google.appengine.api import users

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

# we have to force the use of the local Mako folder rather than the system one
# this is a problem with how Mako does imports (assumes an installed package)
# also, this would never happen on production as Google blocks these things
import os
if os.environ.get('SERVER_SOFTWARE', '').startswith('Development'):
    import sys
    for path in sys.path:
        if 'Mako' in path:
            sys.path.remove(path)
            break
    sys.path.append(BLOG_PATH)

from mako.lookup import TemplateLookup


class BaseController(webapp.RequestHandler):

    template_lookup = TemplateLookup(directories=[TEMPLATES_PATH])

    def cacheAndRenderTemplate(self, filename, **kwargs):
        def renderHTML():
            return self.compileTemplate(filename, **kwargs)
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
        return template.render_unicode(**kwargs)

    def renderTemplate(self, filename, **kwargs):
        self.response.out.write(self.compileTemplate(filename, **kwargs))

    def renderError(self, status_int):
        self.response.set_status(status_int)
        self.response.out.write("You've Encountered An Error: ")
        self.response.out.write(str(status_int) + " - " + self.response.http_status_message(status_int))

    def getUser(self):
        return users.get_current_user()

    def isUserAdmin(self):
        return users.is_current_user_admin()

    def getBlog(self):
        return model.Blog.get_by_key_name(self.blog_slug)

    # helper function for validating comments
    def validate(self, validator, value, name):
        try:
            value = validator.to_python(value)
        except:
            self.renderError(400)
            self.response.out.write(" - Invalid " + name)
            return None
        return value

    @property
    def blog_slug(self):
        return self.request.path.split('/')[1] # we add the slash for easy URL making

    @property
    def blog_url(self):
        return '/' + self.blog_slug

