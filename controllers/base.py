# the base file and class for all controllers to inherit from

# app engine imports
from google.appengine.ext import webapp
from google.appengine.api import users

# local
from gaeblog.config import TEMPLATES_PATH, BLOG_URL
from gaeblog import model

# we have to force the use of the local Mako folder rather than the system one
# this is a problem with how Python 2.X deals with imports - it's fixed in 3.X
# also, this would never happen on production as Google blocks these things
import sys
system_mako = '/usr/local/lib/python2.6/dist-packages/Mako-0.2.5-py2.6.egg'
if system_mako in sys.path:
    sys.path.remove(system_mako)

from mako.lookup import TemplateLookup

class BaseController(webapp.RequestHandler):

    template_lookup = TemplateLookup(directories=[TEMPLATES_PATH])
    def renderTemplate(self, filename, **kwargs):
        template = self.template_lookup.get_template(filename)
        # add some standard variables
        kwargs["blog_url"] = BLOG_URL
        blog = model.Blog.all().get()
        if blog:
            kwargs["blog_title"] = blog.title
            kwargs["blog_comments"] = blog.comments
        user = self.getUser()
        kwargs["user"] = user
        if user:
            kwargs["user_is_admin"] = users.is_current_user_admin()
        self.response.out.write(template.render_unicode(**kwargs))

    def renderError(self, status_int):
        self.response.set_status(status_int)
        self.response.out.write(str(status_int) + " - " + self.response.http_status_message(status_int))

    def getUser(self):
        return users.get_current_user()

