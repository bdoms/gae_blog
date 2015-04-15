import math
from datetime import datetime

from base import BaseController, cacheAndRender
from gae_blog.lib.gae_validators import validateInt

from gae_blog import model


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

        self.renderTemplate('index.html', page=page, last_page=last_page, posts=posts, len=len)


    def getPaginatedPosts(self, entity, posts_per_page, redirect_url):
        published_posts = entity.published_posts

        last_page = int(math.ceil(published_posts.count() / float(posts_per_page)))
        
        try:
            page_str = self.request.get("page")
        except UnicodeDecodeError:
            return self.renderError(400)
        
        try:
            order = self.request.get("order")
        except UnicodeDecodeError:
            return self.renderError(400)

        page = 0
        if page_str:
            valid, page = validateInt(page_str)

            # don't want this for SEO purposes
            if not page:
                return self.redirect(redirect_url, permanent=True)
            # and these don't exist yet
            if page >= last_page:
                return self.renderError(404)
        else:
            page = last_page
        
        if order == 'asc':
            now = datetime.utcnow()
            published_posts = entity.posts.filter(model.BlogPost.published == True) \
                .filter(model.BlogPost.timestamp < now).order(model.BlogPost.timestamp)

        posts = []
        if page:
            # invert the offset so that pages increase as time goes on
            offset_page = last_page - page

            posts = published_posts.fetch(posts_per_page, offset=offset_page * posts_per_page)

        return page, last_page, posts
