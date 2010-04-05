from datetime import datetime

from base import BaseController

from gae_blog import model


class FeedController(BaseController):
    """ handles request for news feeds like RSS """
    def get(self):

        blog = self.getBlog()
        root_url = self.request.headers.get('host')

        self.renderTemplate('feed.rss', blog=blog, root_url=root_url, build_date=datetime.now())

