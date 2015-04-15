from base import cacheAndRender
from index import IndexController

from gae_blog import model


class TagController(IndexController):
    """ handles request for an author's page """

    @cacheAndRender()
    def get(self, tag_slug):

        blog = self.blog
        if not blog:
            return self.renderError(403)

        if tag_slug:
            
            tag = model.BlogTag.get_by_id(tag_slug, parent=blog.key)

            if tag:
                tag_url = self.blog_url + '/tag/' + tag_slug
                result = self.getPaginatedPosts(tag, blog.posts_per_page, tag_url)

                if self.response.status_int != 200:
                    return

                page, last_page, posts = result

                page_title = "Tag - " + tag.name

                return self.renderTemplate('index.html', page=page, last_page=last_page, posts=posts,
                    tag=tag, tag_url=tag_url, page_title=page_title, len=len)

        return self.renderError(404)
