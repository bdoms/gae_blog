from datetime import datetime

from base import BaseController, cacheAndRender


class FeedController(BaseController):
    """ handles request for news feeds like RSS """

    # the minifier does not play nice with RSS - CDATA and camelCased end tags are not handled properly
    # `use_datastore` adds another layer of caching instead of having to render this each time
    @cacheAndRender(minify=False, use_datastore=True)
    def get(self):

        root_url = self.request.headers.get('host')

        self.renderTemplate('feed.rss', blog=self.blog, root_url=root_url, build_date=datetime.utcnow())
