from datetime import datetime

from base import BaseController, cacheAndRender

from gae_blog import model


class FeedController(BaseController):
    """ handles request for news feeds like RSS """

    # the minifier does not play nice with RSS - CDATA and camelCased end tags are not handled properly
    # `use_datastore` adds another layer of caching instead of having to render this each time
    @cacheAndRender(minify=False, use_datastore=True)
    def get(self):

        root_url = self.request.headers.get('host')

        blog = self.blog
        author = None
        tag = None
        posts = []
        if blog:
            entity = blog
            author_slug = self.request.get("author")
            if author_slug and blog.author_pages:
                author = model.BlogAuthor.get_by_id(author_slug, parent=blog.key)
                if author:
                    entity = author
            else:
                tag_slug = self.request.get("tag")
                if tag_slug:
                    tag = model.BlogTag.get_by_id(tag_slug, parent=blog.key)
                    if tag:
                        entity = tag

            posts = entity.published_posts.fetch(blog.posts_per_page)

        self.renderTemplate('feed.rss', blog=blog, author=author, tag=tag,
            posts=posts, root_url=root_url, build_date=datetime.utcnow())
