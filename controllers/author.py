from base import BaseController

from gae_blog import model

class AuthorController(BaseController):
    """ handles request for an author's page """
    def get(self, author_slug):

        if author_slug:
            blog = self.getBlog()
            author = blog.authors.filter("slug =", author_slug).get()

            if author:
                page = 0
                last_page = 0
                posts = []

                page_str = self.request.get("page")
                if page_str:
                    try:
                        page = int(page_str)
                    except:
                        pass

                published_posts = author.published_posts
                posts_per_page = blog.posts_per_page

                last_page = published_posts.count() / posts_per_page - 1
                if last_page < 0:
                    last_page = 0

                posts = published_posts.fetch(posts_per_page, page * posts_per_page)

                self.renderTemplate('index.html', page=page, last_page=last_page, posts=posts, author=author)

        return self.renderError(404)
