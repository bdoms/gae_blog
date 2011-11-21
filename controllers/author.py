from base import BaseController, renderIfCached

from gae_blog import model

class AuthorController(BaseController):
    """ handles request for an author's page """

    @renderIfCached
    def get(self, author_slug):

        if author_slug:
            blog = self.getBlog()
            author = model.BlogAuthor.get_by_key_name(author_slug, parent=blog)

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

                last_page = (published_posts.count() - 1) / posts_per_page
                if last_page < 0:
                    last_page = 0

                posts = published_posts.fetch(posts_per_page, page * posts_per_page)

                page_title = "Author - " + author.name

                return self.cacheAndRenderTemplate('index.html', page=page, last_page=last_page, posts=posts, author=author, page_title=page_title)

        return self.renderError(404)

