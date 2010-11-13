from base import BaseController, renderIfCached

from gae_blog import model

class IndexController(BaseController):
    """ handles request for the main index page of the site """

    @renderIfCached
    def get(self):

        blog = self.getBlog()

        page = 0
        last_page = 0
        posts = []

        if blog:
            page_str = self.request.get("page")
            if page_str:
                try:
                    page = int(page_str)
                except:
                    pass

            published_posts = blog.published_posts
            posts_per_page = blog.posts_per_page

            last_page = (published_posts.count() - 1) / posts_per_page
            if last_page < 0:
                last_page = 0

            posts = published_posts.fetch(posts_per_page, page * posts_per_page)

        self.cacheAndRenderTemplate('index.html', page=page, last_page=last_page, posts=posts)

