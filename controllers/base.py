# the base file and class for all controllers to inherit from

# app engine imports
from google.appengine.ext import webapp
from google.appengine.api import users

# local
from gae_blog.config import TEMPLATES_PATH, BLOG_PATH
from gae_blog import model

# we have to force the use of the local Mako folder rather than the system one
# this is a problem with how Mako does imports (assumes an installed package)
# also, this would never happen on production as Google blocks these things
import sys
for path in sys.path:
    if 'Mako' in path:
        sys.path.remove(path)
        break

sys.path.append(BLOG_PATH)
from mako.lookup import TemplateLookup


class BaseController(webapp.RequestHandler):

    template_lookup = TemplateLookup(directories=[TEMPLATES_PATH])
    def renderTemplate(self, filename, **kwargs):
        template = self.template_lookup.get_template(filename)
        # add some standard variables
        kwargs["blog_url"] = self.blog_url
        kwargs["blog_template"] = ""
        blog = self.getBlog()
        if blog:
            kwargs["blog_title"] = blog.title
            kwargs["blog_description"] = blog.description
            kwargs["blog_comments"] = blog.comments
            kwargs["blog_template"] = blog.template
        user = self.getUser()
        kwargs["user"] = user
        if user:
            kwargs["user_is_admin"] = users.is_current_user_admin()
        self.response.out.write(template.render_unicode(**kwargs))

    def renderError(self, status_int):
        self.response.set_status(status_int)
        self.response.out.write("You've Encountered An Error: ")
        self.response.out.write(str(status_int) + " - " + self.response.http_status_message(status_int))

    def getUser(self):
        return users.get_current_user()

    def getBlog(self):
        return model.Blog.all().filter('url =', self.blog_url).get()

    @property
    def blog_url(self):
        return '/'.join(self.request.path.split('/')[0:2])

