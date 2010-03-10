from base import BaseController

import model

class IndexController(BaseController):
    """ handles request for the main index page of the site """
    def get(self):

        posts = model.Post.all()

        self.renderTemplate('index.html', posts=posts)

