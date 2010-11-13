from datetime import datetime

from base import BaseController, renderIfCached

from gae_blog import model


class FeedController(BaseController):
    """ handles request for news feeds like RSS """

    @renderIfCached
    def get(self):

        blog = self.getBlog()
        root_url = self.request.headers.get('host')

        self.cacheAndRenderTemplate('feed.rss', blog=blog, root_url=root_url, build_date=datetime.now())

