from datetime import datetime

from base import BaseController, renderIfCached


class FeedController(BaseController):
    """ handles request for news feeds like RSS """

    @renderIfCached(use_datastore=True)
    def get(self):

        root_url = self.request.headers.get('host')

        # the minifier does not play nice with RSS - CDATA and camelCased end tags are not handled properly
        # `use_datastore` adds another layer of caching instead of having to render this each time
        self.cacheAndRenderTemplate('feed.rss', minify=False, use_datastore=True,
        	blog=self.blog, root_url=root_url, build_date=datetime.utcnow())
