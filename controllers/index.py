from base import BaseController

from gaeblog import model

class IndexController(BaseController):
    """ handles request for the main index page of the site """
    def get(self):

        blog = self.getBlog()

        self.renderTemplate('index.html', blog=blog)

