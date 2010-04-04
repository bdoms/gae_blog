from datetime import datetime

from google.appengine.api import users

from base import BaseController

from gaeblog import model


class AdminController(BaseController):
    """ shows the index page for the admin section, and handles sitewide configuration """
    def get(self):

        blog = self.getBlog()

        if blog:
            other_blogs = model.Blog.all().filter("url !=", blog.url)
            self.renderTemplate('admin/index.html', blog=blog, other_blogs=other_blogs, logout_url=self.logout_url)

        else:
            self.redirect(self.blog_url + '/admin/blog/')

    @property
    def logout_url(self):
        return users.create_logout_url(self.blog_url)

class BlogController(AdminController):
    """ handles blog configuration and creation """
    def get(self, blog_key):

        blog = None
        if blog_key:
            blog = model.Blog.get(blog_key)

        self.renderTemplate('admin/blog.html', blog=blog, logout_url=self.logout_url)

    def post(self, blog_key):

        blog = None
        if blog_key:
            blog = model.Blog.get(blog_key)

        title = self.request.get("title", "")
        description = self.request.get("description", "")
        url = self.request.get("url", "")
        template = self.request.get("template", "")
        comments = self.request.get("comments", None)

        if comments:
            comments = True
        else:
            comments = False

        if blog:
            blog.title = title
            blog.description = description
            blog.comments = comments
            blog.url = url
            blog.template = template
        else:
            # check to make sure that there isn't already another blog at this URL
            existing = model.Blog.all().filter('url =', url).get()
            if existing:
                self.response.out.write("A blog already exists with that URL.")
                return

            blog = model.Blog(title=title, description=description, comments=comments, url=url, template=template)

        blog.put()

        if blog_key:
            self.redirect(blog.url + '/admin')
        else:
            self.redirect(blog.url + '/admin/author/')


class AuthorsController(AdminController):
    """ handles viewing all authors for this blog """
    def get(self):

        blog = self.getBlog()
        authors = model.BlogAuthor.all().filter('blog =', blog)

        self.renderTemplate('admin/authors.html', authors=authors, logout_url=self.logout_url)


class AuthorController(AdminController):
    """ handles creating and changing authors """
    def get(self, author_key):

        author = None
        if author_key:
            author = model.BlogAuthor.get(author_key)

        self.renderTemplate('admin/author.html', author=author, logout_url=self.logout_url)

    def post(self, author_key):

        author = None
        if author_key:
            author = model.BlogAuthor.get(author_key)

        name = self.request.get("name")
        url = self.request.get("url")
        email = self.request.get("email")

        if author:
            author.name = name
            author.url = url
            author.email = email
        else:
            author = model.BlogAuthor(name=name, url=url, email=email, blog=self.getBlog())

        author.put()

        self.redirect(self.blog_url + '/admin')


class PostsController(AdminController):
    """ handles viewing all posts for this blog """
    def get(self):

        posts = self.getBlog().posts

        self.renderTemplate('admin/posts.html', posts=posts, logout_url=self.logout_url)


class PostController(AdminController):
    """ handles editing and publishing posts """
    def get(self, post_slug):

        blog = self.getBlog()
        post = None
        if post_slug:
            post = model.BlogPost.all().filter("blog =", blog).filter("slug =", post_slug).get()

        authors = model.BlogAuthor.all().filter("blog =", blog)

        self.renderTemplate('admin/post.html', post=post, authors=authors, logout_url=self.logout_url)

    def post(self, post_slug):

        title = self.request.get("title")
        author = self.request.get("author")
        body = self.request.get("body")
        timestamp_choice = self.request.get("timestamp-choice")
        timestamp = self.request.get("timestamp")
        published = self.request.get("published", None)

        author = model.BlogAuthor.get(author)

        if timestamp_choice == "now":
            timestamp = datetime.utcnow()
        else:
            # try to parse it
            timestamp = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")

        if published:
            published = True
        else:
            published = False

        blog = self.getBlog()

        post = None
        if post_slug:
            post = model.BlogPost.all().filter("blog =", blog).filter("slug =", post_slug).get()

        if post:
            post.title = title
            post.body = body
            post.timestamp = timestamp
            post.published = published
            post.slug = model.makePostSlug(title, post)
            post.author = author
        else:
            post = model.BlogPost(title=title, body=body, timestamp=timestamp, published=published, slug=model.makePostSlug(title), author=author, blog=blog)

        post.put()

        # send them back to the admin list of posts if it's not published or to the actual post if it is
        if post.published:
            self.redirect(self.blog_url + '/post/' + post.slug)
        else:
            self.redirect(self.blog_url + '/admin/posts')


class CommentsController(AdminController):
    """ handles moderating comments """
    def get(self):

        comments = []
        for post in self.getBlog().posts:
            comments.extend(list(post.comments.filter("approved =", False)))

        self.renderTemplate('admin/comments.html', comments=comments, logout_url=self.logout_url)

    def post(self):

        # approve all the comments with the submitted email address here
        email = self.request.get("email")

        comments = []
        for post in self.getBlog().posts:
            comments.extend(list(post.comments.filter("email =", email)))

        for comment in comments:
            comment.approved = True
            comment.put()

        self.redirect(self.blog_url + '/admin/comments')

