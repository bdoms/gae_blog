from google.appengine.api import users

from base import BaseController, BLOG_URL

from gaeblog import model

LOGOUT_URL = users.create_logout_url("/")


class AdminController(BaseController):
    """ shows the index page for the admin section, and handles sitewide configuration """
    def get(self):

        self.renderTemplate('admin/index.html')

    def post(self):

        title = self.request.get("title")
        comments = self.request.get("comments", None)

        if comments:
            comments = True
        else:
            comments - False

        blog = model.Blog.all().get()
        if blog:
            blog.title = title
            blog.comments = comments
        else:
            blog = model.Blog(title=title, comments=comments)

        blog.put()

        self.redirect(BLOG_URL + '/admin')


class PostsController(BaseController):
    """ handles viewing all posts """
    def get(self):

        posts = model.Post.all()

        self.renderTemplate('admin/posts.html', posts=posts)


class PostController(BaseController):
    """ handles editing and publishing posts """
    def get(self, post_slug):

        post = None
        if post_slug:
            post = model.Post.all().filter("slug =", post_slug).get()

        self.renderTemplate('admin/post.html', post=post)

    def post(self, post_slug):

        title = self.request.get("title")
        body = self.request.get("body")
        published = self.request.get("published", None)

        if published:
            published = True
        else:
            published = False

        post = None
        if post_slug:
            post = model.Post.all().filter("slug =", post_slug).get()

        if post:
            post.title = title
            post.body = body
            post.published = published
            post.slug = model.makePostSlug(title, post)
        else:
            post = model.Post(title=title, body=body, published=published, slug=model.makePostSlug(title))

        post.put()

        # send them back to the admin list of posts if it's not published or to the actual post if it is
        if post.published:
            self.redirect(BLOG_URL + '/post/' + post.slug)
        else:
            self.redirect(BLOG_URL + '/admin/posts')


class CommentsController(BaseController):
    """ handles moderating comments """
    def get(self):

        comments = model.Comment.all().filter("approved =", False)

        self.renderTemplate('admin/comments.html', comments=comments)

    def post(self):

        # approve all the comments with the submitted email address here
        email = self.request.get("email")

        comments = model.Comment.all().filter("email =", email)
        for comment in comments:
            comment.approved = True
            comment.put()

        self.redirect(BLOG_URL + '/admin/comments')

