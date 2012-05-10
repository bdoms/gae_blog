from datetime import datetime

from google.appengine.api import users, memcache
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers

from base import BaseController

from gae_blog import model
from gae_blog.formencode.validators import Email, Int, URL, UnicodeString


class AdminController(BaseController):
    """ shows the index page for the admin section, and handles sitewide configuration """

    # override and add in a check to make sure the user accessing this page has admin privileges
    def __getattribute__(self, name):
        if name in ["get", "post"] and not self.isUserAdmin():
            self.renderError(403)
            def pass_through(*args, **kwargs): pass
            return pass_through
        return BaseController.__getattribute__(self, name)

    def get(self):

        blog = self.getBlog()

        if blog:
            other_blogs = [b for b in model.Blog.all() if b.slug != blog.slug]
            self.renderTemplate('admin/index.html', blog=blog, other_blogs=other_blogs, page_title="Admin", logout_url=self.logout_url)

        else:
            self.redirect(self.blog_url + '/admin/blog')

    @property
    def logout_url(self):
        return users.create_logout_url(self.blog_url)


class BlogController(AdminController):
    """ handles blog configuration and creation """
    def get(self):

        form_data, errors = self.errorsFromSession()

        self.renderTemplate('admin/blog.html', form_data=form_data, errors=errors, page_title="Admin - Blog", logout_url=self.logout_url)

    def post(self):

        blog = self.getBlog()

        title = self.request.get("title", "")
        description = self.request.get("description", "")
        url = self.request.get("url", "")
        template = self.request.get("template", "")
        blocklist = self.request.get("blocklist", "")
        enable_comments = self.request.get("enable_comments", None)
        moderation_alert = self.request.get("moderation_alert", None)
        contact = self.request.get("contact", None)
        admin_email = self.request.get("admin_email", "")
        posts_per_page = self.request.get("posts_per_page", None)
        image_preview_size = self.request.get("image_preview_size", None)

        errors = {}
        form_data = {"title": title, "description": description, "url": url, "template": template, "blocklist": blocklist,
                     "enable_comments": enable_comments, "moderation_alert": moderation_alert, "contact": contact,
                     "admin_email": admin_email, "posts_per_page": posts_per_page, "image_preview_size": image_preview_size}

        title = self.validate(UnicodeString(not_empty=True), title)
        if not title: errors["title"] = True

        if description:
            description = self.validate(UnicodeString(), description)
            if not description: errors["description"] = True

        url = self.validate(UnicodeString(not_empty=True), url)
        if url:
            if not blog or url != blog.slug:
                # check to make sure that there isn't already another blog at this URL
                existing = model.Blog.get_by_key_name(url)
                if existing: errors["url_exists"] = True
        else:
            errors["url"] = True

        if template:
            template = self.validate(UnicodeString(), template)
            if not template: errors["template"] = True

        posts_per_page = self.validate(Int(), posts_per_page)
        if not posts_per_page: errors["posts_per_page"] = True

        image_preview_size = self.validate(Int(), image_preview_size)
        if not image_preview_size: errors["image_preview_size"] = True

        if admin_email:
            admin_email = self.validate(Email(), admin_email)
            if not admin_email: errors["admin_email"] = True

        if errors:
            self.errorsToSession(form_data, errors)
            return self.redirect(self.blog_url + '/admin/blog')

        if blocklist:
            blocklist = blocklist.split("\n")
        else:
            blocklist = []

        if enable_comments:
            enable_comments = True
        else:
            enable_comments = False

        if moderation_alert:
            moderation_alert = True
        else:
            moderation_alert = False

        if contact:
            contact = True
        else:
            contact = False

        if blog:
            # if the URL is different, remake the entities since the key name needs to change
            if url != blog.slug:
                blog = model.makeNew(blog, key_name=url, use_transaction=False) # each blog is its own entity group, so can't run in a transaction
            blog.title = title
            blog.description = description
            blog.enable_comments = enable_comments
            blog.moderation_alert = moderation_alert
            blog.contact = contact
            blog.admin_email = admin_email
            blog.posts_per_page = posts_per_page
            blog.image_preview_size = image_preview_size
            blog.template = template
            blog.blocklist = blocklist
            existed = True
        else:
            blog = model.Blog(key_name=url, title=title, description=description, enable_comments=enable_comments, moderation_alert=moderation_alert,
                              contact=contact, admin_email=admin_email, posts_per_page=posts_per_page, image_preview_size=image_preview_size,
                              template=template, blocklist=blocklist)
            existed = False

        blog.put()
        memcache.flush_all()

        if existed:
            self.redirect('/' + blog.slug + '/admin')
        else:
            self.redirect('/' + blog.slug + '/admin/author/')


class AuthorsController(AdminController):
    """ handles viewing all authors for this blog """
    def get(self):

        blog = self.getBlog()
        authors = blog.authors.order('name')

        self.renderTemplate('admin/authors.html', authors=authors, page_title="Admin - Authors", logout_url=self.logout_url)


class AuthorController(AdminController):
    """ handles creating and changing authors """
    def get(self, author_slug):

        author = None
        page_title = "Admin - Author"
        if author_slug:
            author = model.BlogAuthor.get_by_key_name(author_slug, parent=self.getBlog())
            if not author:
                return self.renderError(404)
            page_title += " - " + author.name

        form_data, errors = self.errorsFromSession()

        self.renderTemplate('admin/author.html', author=author, form_data=form_data, errors=errors, page_title=page_title, logout_url=self.logout_url)

    def post(self, author_slug):

        blog = self.getBlog()
        author = None
        if author_slug:
            author = model.BlogAuthor.get_by_key_name(author_slug, parent=blog)
            if not author:
                return self.renderError(404)

        name = self.request.get("name")
        url = self.request.get("url")
        email = self.request.get("email")

        errors = {}
        form_data = {"name": name, "url": url, "email": email}

        name = self.validate(UnicodeString(not_empty=True), name)
        if not name: errors["name"] = True

        if url:
            url = self.validate(URL(add_http=True), url)
            if not url: errors["url"] = True

        if email:
            email = self.validate(Email(), email)
            if not email: errors["email"] = True

        if errors:
            self.errorsToSession(form_data, errors)
            return self.redirect(self.blog_url + '/admin/author/' + author_slug)

        slug = model.makeAuthorSlug(name, blog, author)
        if author:
            # if the name is different, remake the entity since the key name needs to change
            if name != author.name:
                # get lists of other entities to update (must be outside of transaction since they're a non-ancestor query)
                posts = list(author.posts)
                comments = list(author.comments)
                # update all the posts and comments referencing the author at the same time that a new author object is created
                def author_transaction(author, slug, blog, ref_lists):
                    # re-create the author object
                    author = model.makeNew(author, key_name=slug, parent=blog, use_transaction=False) # no nested transactions
                    # update the others to reference the new object
                    for ref_list in ref_lists:
                        new_objects = []
                        for ref_object in ref_list:
                            ref_object.author = author
                            new_objects.append(ref_object)
                        model.db.put(new_objects)
                    return author
                author = model.db.run_in_transaction(author_transaction, author, slug, blog, [posts, comments])
            author.name = name
            author.url = url
            author.email = email
        else:
            author = model.BlogAuthor(key_name=slug, name=name, url=url, email=email, parent=blog)

        author.put()
        memcache.flush_all()

        if blog.authors.count() > 1:
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
            post = model.BlogPost.get_by_key_name(post_key, parent=self.getBlog())
            if post:
                # delete all the post's comments first
                if post.comments.count() > 0:
                    model.db.delete(list(post.comments))
                # then the post itself
                post.delete()
                memcache.flush_all()
            else:
                return self.renderError(404)

        self.redirect(self.blog_url + '/admin/posts')

class PostController(AdminController):
    """ handles editing and publishing posts """
    def get(self, post_slug):

        blog = self.getBlog()
        post = None
        if post_slug:
            post = model.BlogPost.get_by_key_name(post_slug, parent=blog)
            if not post:
                return self.renderError(404)

        form_data, errors = self.errorsFromSession()

        self.renderTemplate('admin/post.html', post=post, form_data=form_data, errors=errors, page_title="Admin - Post", logout_url=self.logout_url)

    def post(self, post_slug):

        blog = self.getBlog()
        post = None
        if post_slug:
            post = model.BlogPost.get_by_key_name(post_slug, parent=blog)
            if not post:
                return self.renderError(404)

        title = self.request.get("title")
        slug_choice = self.request.get("slug-choice")
        slug = self.request.get("slug")
        author_slug = self.request.get("author")
        body = self.request.get("body")
        timestamp_choice = self.request.get("timestamp-choice")
        timestamp = self.request.get("timestamp")
        published = self.request.get("published", None)

        errors = {}
        form_data = {"title": title, "slug-choice": slug_choice, "slug": slug, "author": author_slug, "body": body,
                     "timestamp-choice": timestamp_choice, "timestamp": timestamp, "published": published}

        title = self.validate(UnicodeString(not_empty=True), title)
        if not title: errors["title"] = True

        if slug_choice == "custom":
            slug = self.validate(UnicodeString(not_empty=True), slug)
            if slug:
                # check to make sure that there isn't already another post with this slug
                existing = model.BlogPost.get_by_key_name(slug, parent=blog)
                if existing and (not post or existing.key() != post.key()):
                    errors["slug_exists"] = True
            else:
                errors["slug"] = True

        author = model.BlogAuthor.get_by_key_name(author_slug, parent=blog)
        if not author: errors["author"] = True

        if body:
            body = self.validate(UnicodeString(), body)
            if not body: errors["body"] = True

        if timestamp_choice == "now":
            timestamp = datetime.utcnow()
        else:
            # try to parse it
            try:
                timestamp = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            except:
                errors["timestamp"] = True

        if errors:
            self.errorsToSession(form_data, errors)
            return self.redirect(self.blog_url + '/admin/post/' + post_slug)

        if published:
            published = True
        else:
            published = False

        if slug_choice == "auto":
            slug = model.makePostSlug(title, blog, post)

        if post:
            # if the slug is different, remake the entities since the key name needs to change
            if slug != post.slug:
                post = model.makeNew(post, key_name=slug, parent=blog)
            post.title = title
            post.body = body
            post.timestamp = timestamp
            post.published = published
            post.author = author
        else:
            post = model.BlogPost(key_name=slug, title=title, body=body, timestamp=timestamp, published=published, author=author, parent=blog)

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
            post = model.BlogPost.get_by_key_name(post_slug, parent=blog)
            if post:
                return self.renderTemplate('admin/preview.html', post=post, logout_url=self.logout_url)

        self.renderError(404)


class CommentsController(AdminController):
    """ handles moderating comments """
    def get(self):

        comments = self.getBlog().comments.filter("approved =", False)

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
            else:
                return self.renderError(404)

            # return them to the post they were viewing if this was deleted from a post page
            post_slug = self.request.get("post")
            if post_slug:
                return self.redirect(self.blog_url + '/post/' + post_slug + '#comments')
        else:
            # approve all the comments with the submitted email address here
            email = self.request.get("email")

            comments = self.getBlog().comments.filter("email =", email)

            for comment in comments:
                comment.approved = True
                comment.put()

        self.redirect(self.blog_url + '/admin/comments')


class ImagesController(AdminController):
    """ handles managing images """
    def get(self):

        blog = self.getBlog()

        page = 0
        last_page = 0
        images = []

        if blog:
            page_str = self.request.get("page")
            if page_str:
                try:
                    page = int(page_str)
                except:
                    pass

            blog_images = blog.images
            images_per_page = blog.posts_per_page

            last_page = (blog_images.count() - 1) / images_per_page
            if last_page < 0:
                last_page = 0

            images = blog_images.order("-timestamp").fetch(images_per_page, page * images_per_page)

        self.renderTemplate('admin/images.html', page=page, last_page=last_page, images=images,
                            page_title="Admin - Images", logout_url=self.logout_url)

    def post(self):

        image_key = self.request.get("image")
        if image_key:
            image = model.BlogImage.get(image_key)
            if image:
                # delete children first
                image.blob.delete()
                # then this one
                image.delete()
            else:
                return self.renderError(404)

        self.redirect(self.blog_url + '/admin/images')


class ImageController(AdminController, blobstore_handlers.BlobstoreUploadHandler):
    """ handles uploading images """

    def get(self):

        upload_url = blobstore.create_upload_url(self.blog_url + '/admin/image')
        page_title = "Admin - Upload an Image"

        form_data, errors = self.errorsFromSession()

        self.renderTemplate('admin/image.html', upload_url=upload_url, errors=errors, page_title=page_title, logout_url=self.logout_url)

    def post(self):
        upload_files = self.get_uploads('data')  # 'data' is file upload field in the form
        errors = {}

        if upload_files:
            blob_info = upload_files[0]
            name = model.checkImageName(blob_info.filename)
            if not name:
                errors["type"] = True

            if errors:
                blob_info.delete()
        else:
            errors["file"] = True

        if errors:
            self.errorsToSession({}, errors)
            return self.redirect(self.blog_url + '/admin/image')

        image = model.BlogImage(parent=self.getBlog(), blob=blob_info)
        image.put()

        self.redirect(self.blog_url + '/admin/images')

