from base import cacheAndRender
from index import IndexController

from gae_blog import model


class AuthorController(IndexController):
    """ handles request for an author's page """

    @cacheAndRender()
    def get(self, author_slug):

        blog = self.blog
        if not blog or not blog.author_pages:
            return self.renderError(403)

        if author_slug:
            
            author = model.BlogAuthor.get_by_id(author_slug, parent=blog.key)

            if author:
                author_url = self.blog_url + '/author/' + author_slug
                result = self.getPaginatedPosts(author, blog.posts_per_page, author_url)

                if self.response.status_int != 200:
                    return

                page, last_page, posts = result

                page_title = "Author - " + author.name

                return self.renderTemplate('index.html', page=page, last_page=last_page, posts=posts,
                    author=author, author_url=author_url, page_title=page_title, len=len)

        return self.renderError(404)
