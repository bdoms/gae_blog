from datetime import datetime

from google.appengine.api import users, memcache

from base import BaseController

from gae_blog import model
from gae_blog.formencode.validators import Email, URL


class AdminController(BaseController):
    """ shows the index page for the admin section, and handles sitewide configuration """
    def get(self):

        blog = self.getBlog()

        if blog:
            other_blogs = model.Blog.all().filter("url !=", blog.url)
            self.renderTemplate('admin/index.html', blog=blog, other_blogs=other_blogs, page_title="Admin", logout_url=self.logout_url)

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

        self.renderTemplate('admin/blog.html', blog=blog, page_title="Admin - Blog", logout_url=self.logout_url)

    def post(self, blog_key):

        blog = None
        if blog_key:
            blog = model.Blog.get(blog_key)

        title = self.request.get("title", "")
        description = self.request.get("description", "")
        url = self.request.get("url", "")
        template = self.request.get("template", "")
        blocklist = self.request.get("blocklist", "")
        comments = self.request.get("comments", None)
        moderation_alert = self.request.get("moderation_alert", None)
        contact = self.request.get("contact", None)
        admin_email = self.request.get("admin_email", "")
        posts_per_page = self.request.get("posts_per_page", None)
        image_preview_width = self.request.get("image_preview_width", None)
        image_preview_height = self.request.get("image_preview_height", None)

        try:
            posts_per_page = int(posts_per_page)
        except:
            self.renderError(400)
            self.response.out.write(" - Posts Per Page value wasn't an integer.")
            return

        try:
            image_preview_width = int(image_preview_width)
        except:
            self.renderError(400)
            self.response.out.write(" - Image Preview Width value wasn't an integer.")
            return

        try:
            image_preview_height = int(image_preview_height)
        except:
            self.renderError(400)
            self.response.out.write(" - Image Preview Height value wasn't an integer.")
            return

        if blocklist:
            blocklist = blocklist.split("\n")
        else:
            blocklist = []

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
            blog.image_preview_width = image_preview_width
            blog.image_preview_height = image_preview_height
            blog.url = url
            blog.template = template
            blog.blocklist = blocklist
        else:
            # check to make sure that there isn't already another blog at this URL
            existing = model.Blog.all().filter('url =', url).get()
            if existing:
                self.renderError(400)
                self.response.out.write(" - A blog already exists with that URL.")
                return

            blog = model.Blog(title=title, description=description, comments=comments, moderation_alert=moderation_alert, contact=contact,
                              admin_email=admin_email, posts_per_page=posts_per_page, image_preview_width=image_preview_width,
                              image_preview_height=image_preview_height, url=url, template=template, blocklist=blocklist)

        blog.put()
        memcache.flush_all()

        if blog_key:
            self.redirect(blog.url + '/admin')
        else:
            self.redirect(blog.url + '/admin/author/')


class AuthorsController(AdminController):
    """ handles viewing all authors for this blog """
    def get(self):

        blog = self.getBlog()
        authors = model.BlogAuthor.all().filter('blog =', blog).order('name')

        self.renderTemplate('admin/authors.html', authors=authors, page_title="Admin - Authors", logout_url=self.logout_url)


class AuthorController(AdminController):
    """ handles creating and changing authors """
    def get(self, author_key):

        author = None
        page_title = "Admin - Author"
        if author_key:
            author = model.BlogAuthor.get(author_key)
            page_title += " - " + author.name

        self.renderTemplate('admin/author.html', author=author, page_title=page_title, logout_url=self.logout_url)

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

        blog = self.getBlog()

        if author:
            author.name = name
            author.url = url
            author.email = email
            author.slug = model.makeAuthorSlug(name, blog, author)
        else:
            author = model.BlogAuthor(name=name, url=url, email=email, slug=model.makeAuthorSlug(name, blog), blog=blog)

        author.put()
        memcache.flush_all()

        if model.BlogAuthor.all().count() > 1:
            self.redirect(self.blog_url + '/admin/authors')

        else:
            self.redirect(self.blog_url + '/admin')


class PostsController(AdminController):
    """ handles viewing all posts for this blog """
    def get(self):

        posts = self.getBlog().posts.order('-timestamp')

        self.renderTemplate('admin/posts.html', posts=posts, page_title="Admin - Posts", logout_url=self.logout_url)

    def post(self):

        post_key = self.request.get("post")
        if post_key:
            # this is a request to delete this post
            post = model.BlogPost.get(post_key)
            if post:
                # delete all the post's comments first
                if post.comments.count() > 0:
                    model.db.delete(list(post.comments))
                # then the post itself
                post.delete()
                memcache.flush_all()

        self.redirect(self.blog_url + '/admin/posts')

class PostController(AdminController):
    """ handles editing and publishing posts """
    def get(self, post_slug):

        blog = self.getBlog()
        post = None
        if post_slug:
            post = blog.posts.filter("slug =", post_slug).get()

        authors = model.BlogAuthor.all().filter("blog =", blog)

        self.renderTemplate('admin/post.html', post=post, authors=authors, page_title="Admin - Post", logout_url=self.logout_url)

    def post(self, post_slug):

        title = self.request.get("title")
        slug_choice = self.request.get("slug-choice")
        slug = self.request.get("slug")
        author_key = self.request.get("author")
        body = self.request.get("body")
        timestamp_choice = self.request.get("timestamp-choice")
        timestamp = self.request.get("timestamp")
        published = self.request.get("published", None)

        blog = self.getBlog()

        post = None
        if post_slug:
            post = blog.posts.filter("slug =", post_slug).get()

        if slug_choice == "custom":
            # check to make sure that there isn't already another post with this slug
            existing = blog.posts.filter('slug =', slug).get()
            if existing and (not post or existing.key() != post.key()):
                self.renderError(400)
                self.response.out.write(" - A post already exists with that slug.")
                return

        author = model.BlogAuthor.get(author_key)

        if timestamp_choice == "now":
            timestamp = datetime.utcnow()
        else:
            # try to parse it
            timestamp = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")

        if published:
            published = True
        else:
            published = False

        if post:
            post.title = title
            post.body = body
            post.timestamp = timestamp
            post.published = published
            if slug_choice == "auto":
                slug = model.makePostSlug(title, blog, post)
            post.slug = slug
            post.author = author
        else:
            if slug_choice == "auto":
                slug = model.makePostSlug(title, blog)
            post = model.BlogPost(title=title, body=body, timestamp=timestamp, published=published, slug=slug, author=author, blog=blog)

        post.put()

        # send them back to the admin list of posts if it's not published or to the actual post if it is
        if post.published:
            memcache.flush_all()
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
            post = blog.posts.filter("slug =", post_slug).get()
            if post:
                return self.renderTemplate('admin/preview.html', post=post, logout_url=self.logout_url)

        self.renderError(404)


class CommentsController(AdminController):
    """ handles moderating comments """
    def get(self):

        comments = []
        for post in self.getBlog().posts:
            comments.extend(list(post.comments.filter("approved =", False)))

        self.renderTemplate('admin/comments.html', comments=comments, page_title="Admin - Comments", logout_url=self.logout_url)

    def post(self):
        memcache.flush_all()
        comment_key = self.request.get("comment")
        if comment_key:
            # delete this individual comment
            comment = model.BlogComment.get(comment_key)
            if comment:
                block = self.request.get("block")
                if block:
                    # also block the IP address
                    blog = self.getBlog()
                    if comment.ip_address and comment.ip_address not in blog.blocklist:
                        blog.blocklist.append(comment.ip_address)
                        blog.put()
                comment.delete()

            # return them to the post they were viewing if this was deleted from a post page
            post_slug = self.request.get("post")
            if post_slug:
                return self.redirect(self.blog_url + '/post/' + post_slug + '#comments')
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


class ImagesController(AdminController):
    """ handles managing images """
    def get(self):

        self.renderTemplate('admin/images.html', page_title="Admin - Images", logout_url=self.logout_url)

    def post(self):

        image_key = self.request.get("image")
        if image_key:
            image = model.BlogImage.get(image_key)
            if image:
                # invalidate the cache (preview and chunk indexes)
                key = image.blog.url + "/img/" + image.name
                memcache.delete_multi((key, key + "?preview=1"))

                # delete children first
                for image_data in image.image_datas:
                    image_data.delete()
                # then this one
                image.delete()

        self.redirect(self.blog_url + '/admin/images')

class ImageController(AdminController):
    """ handles uploading or editing images """
    def get(self, image_name):

        blog = self.getBlog()
        image = None
        page_title = "Admin - Image"
        if image_name:
            image = blog.images.filter("name =", image_name).get()
            page_title += " - " + image.name

        self.renderTemplate('admin/image.html', image=image, page_title=page_title, logout_url=self.logout_url)

    def post(self, image_name):

        blog = self.getBlog()

        image = None
        if image_name:
            image = blog.images.filter("name =", image_name).get()

        name = self.request.get("name")
        timestamp = self.request.get("timestamp")
        data = self.request.get("data")

        name = model.checkImageName(name, blog, image)
        if not name:
            self.renderError(400)
            self.response.out.write(" - Invalid filename: duplicate or bad extension.")
            return

        if not timestamp:
            timestamp = datetime.utcnow()
        else:
            # try to parse it
            timestamp = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")

        if image:
            # invalidate the cache (preview and chunk indexes)
            key = blog.url + "/img/" + image.name
            memcache.delete_multi((key, key + "?preview=1"))

            if data:
                image.setData(data, blog)
            image.name = name
            image.timestamp = timestamp
            image.put()
        else:
            if not data:
                self.renderError(400)
                self.response.out.write(" - No file selected.")
                return
            image = model.BlogImage(name=name, timestamp=timestamp, blog=blog)
            image.put() # needs to be in the DB so that setData can add entities that reference it
            image.setData(data, blog)

        self.redirect(self.blog_url + '/admin/images')

