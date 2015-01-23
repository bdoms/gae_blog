import math

from base import BaseController, cacheAndRender


class IndexController(BaseController):
    """ handles request for the main index page of the site """

    @cacheAndRender()
    def get(self):

        blog = self.blog

        page = 0
        last_page = 0
        posts = []

        if blog:
            result = self.getPaginatedPosts(blog, blog.posts_per_page, self.blog_slug)

            if self.response.status_int != 200:
                return

            page, last_page, posts = result

        return self.compileTemplate('index.html', page=page, last_page=last_page, posts=posts, len=len)


    def getPaginatedPosts(self, entity, posts_per_page, redirect_url):
        published_posts = entity.published_posts

        last_page = int(math.ceil(published_posts.count() / float(posts_per_page)))
        
        page = 0
        page_str = self.request.get("page")
        if page_str:
            try:
                page = int(page_str)
            except:
                pass

            # don't want this for SEO purposes
            if not page:
                return self.redirect(redirect_url, permanent=True)
            # and these don't exist yet
            if page >= last_page:
                return self.renderError(404)
        else:
            page = last_page
        
        posts = []
        if page:
            # invert the offset so that pages increase as time goes on
            offset_page = last_page - page

            posts = published_posts.fetch(posts_per_page, offset=offset_page * posts_per_page)

        return page, last_page, posts
