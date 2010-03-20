from base import BaseController

from gaeblog import model

class IndexController(BaseController):
    """ handles request for the main index page of the site """
    def get(self):

        posts = model.BlogPost.all()

        self.renderTemplate('index.html', posts=posts)

