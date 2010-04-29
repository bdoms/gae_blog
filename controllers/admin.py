from datetime import datetime

from google.appengine.api import users

from base import BaseController

from gae_blog import model
from gae_blog.formencode.validators import Email


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
        moderation_alert = self.request.get("moderation_alert", None)
        contact = self.request.get("contact", None)
        admin_email = self.request.get("admin_email", "")
        posts_per_page = self.request.get("posts_per_page", None)

        try:
            posts_per_page = int(posts_per_page)
        except:
            self.renderError(400)
            self.response.out.write(" - Posts Per Page value wasn't an integer.")
            return

        if comments:
            comments = True
        else:
            comments = False

        if moderation_alert:
            moderation_alert = True
        else:
            moderation_alert = False

        if contact:
            contact = True
        else:
            contact = False

        if blog:
            blog.title = title
            blog.description = description
            blog.comments = comments
            blog.moderation_alert = moderation_alert
            blog.contact = contact
            blog.admin_email = admin_email
            blog.posts_per_page = posts_per_page
            blog.url = url
            blog.template = template
        else:
            # check to make sure that there isn't already another blog at this URL
            existing = model.Blog.all().filter('url =', url).get()
            if existing:
                self.renderError(400)
                self.response.out.write(" - A blog already exists with that URL.")
                return

            blog = model.Blog(title=title, description=description, comments=comments, moderation_alert=moderation_alert,
                              contact=contact, admin_email=admin_email, posts_per_page=posts_per_page, url=url, template=template)

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

        if url:
            url = self.validate(URL(add_http=True), url, "URL")

        if email:
            email = self.validate(Email(), email, "Email")

        if author:
            author.name = name
            author.url = url
            author.email = email
        else:
            author = model.BlogAuthor(name=name, url=url, email=email, blog=self.getBlog())

        author.put()

        if model.BlogAuthor.all().count() > 1:
            self.redirect(self.blog_url + '/admin/authors')

        else:
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
            if self.request.get("preview"):
                self.redirect(self.blog_url + '/admin/preview/' + post.slug)
            else:
                self.redirect(self.blog_url + '/admin/posts')


class PreviewController(AdminController):
    """ handles showing an admin-only preview of a post """
    def get(self, post_slug):

        blog = self.getBlog()
        post = None
        if post_slug:
            post = model.BlogPost.all().filter("blog =", blog).filter("slug =", post_slug).get()
            if post:
                return self.renderTemplate('admin/preview.html', post=post, logout_url=self.logout_url)

        self.renderError(404)


class CommentsController(AdminController):
    """ handles moderating comments """
    def get(self):

        comments = []
        for post in self.getBlog().posts:
            comments.extend(list(post.comments.filter("approved =", False)))

        self.renderTemplate('admin/comments.html', comments=comments, logout_url=self.logout_url)

    def post(self):

        comment_key = self.request.get("comment")
        if comment_key:
            # delete this individual comment
            comment = model.BlogComment.get(comment_key)
            if comment:
                comment.delete()
        else:
            # approve all the comments with the submitted email address here
            email = self.request.get("email")

            comments = []
            for post in self.getBlog().posts:
                comments.extend(list(post.comments.filter("email =", email)))

            for comment in comments:
                comment.approved = True
                comment.put()

        self.redirect(self.blog_url + '/admin/comments')

