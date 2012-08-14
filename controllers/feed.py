from datetime import datetime

from base import BaseController, renderIfCached


class FeedController(BaseController):
    """ handles request for news feeds like RSS """

    @renderIfCached
    def get(self):

        blog = self.getBlog()
        root_url = self.request.headers.get('host')

        # the minifier does not play nice with RSS - CDATA and camelCased end tags are not handled properly
        self.cacheAndRenderTemplate('feed.rss', minify=False, blog=blog, root_url=root_url, build_date=datetime.now())

