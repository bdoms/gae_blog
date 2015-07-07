from datetime import datetime

from google.appengine.api import users, memcache, images
from google.appengine.ext import blobstore, ndb
from google.appengine.ext.webapp import blobstore_handlers

from base import FormController

from gae_blog.lib.gae_validators import (validateString, validateRequiredString, validateText, validateEmail,
    validateUrl, validateInt, validateBool, validateDateTime)
from gae_blog import model


def validateDT(source):
    if not source:
        return True, None
    else:
        return validateDateTime(source, date_format="%Y-%m-%d %H:%M:%S", future_only=False)


class AdminController(FormController):
    """ shows the index page for the admin section, and handles sitewide configuration """

    # override and add in a check to make sure the user accessing this page has admin privileges
    def dispatch(self):
        if not self.user_is_admin:
            self.renderError(403)
        else:
            super(AdminController, self).dispatch()

    def get(self):

        blog = self.blog

        if blog:
            other_blogs = [b for b in model.Blog.query() if b.slug != blog.slug]
            self.renderTemplate('admin/index.html', blog=blog, other_blogs=other_blogs, page_title="Admin", logout_url=self.logout_url)

        else:
            self.redirect(self.blog_url + '/admin/blog')

    @property
    def logout_url(self):
        url = None
        if users.get_current_user():
            url = users.create_logout_url(self.blog_url)
        return url


class BlogController(AdminController):
    """ handles blog configuration and creation """

    FIELDS = {"title": validateRequiredString, "description": validateString, "url": validateRequiredString,
        "template": validateString, "posts_per_page": validateInt, "image_preview_size": validateInt,
        "mail_queue": validateRequiredString, "blocklist": validateText, "enable_comments": validateBool,
        "enable_linkbacks": validateBool, "author_pages": validateBool, "admin_email": validateEmail,
        "moderation_alert": validateBool, "contact": validateBool}

    def get(self):

        form_data, errors = self.errorsFromSession()

        self.renderTemplate('admin/blog.html', form_data=form_data, errors=errors, page_title="Admin - Blog", logout_url=self.logout_url)

    def post(self):

        blog = self.blog

        form_data, errors, valid_data = self.validate()

        if "url" not in errors:
            if not blog or valid_data["url"] != blog.slug:
                # check to make sure that there isn't already another blog at this URL
                existing = model.Blog.get_by_id(valid_data["url"])
                if existing:
                    errors["url_exists"] = True

        if errors:
            return self.redisplay(form_data, errors, self.blog_url + '/admin/blog')

        if valid_data["blocklist"]:
            blocklist = valid_data["blocklist"].split("\r\n")
            valid_data["blocklist"] = [ip for ip in blocklist if ip] # remove empty lines
        else:
            valid_data["blocklist"] = []

        url = valid_data["url"]
        del valid_data["url"]

        if blog:
            # if the URL is different, remake the entities since the key name needs to change
            if url != blog.slug:
                # each blog is its own entity group, so can't run in a transaction
                blog = model.makeNew(blog, id=url, use_transaction=False)
            blog.populate(**valid_data)
            existed = True
        else:
            blog = model.Blog(id=url, **valid_data)
            existed = False

        blog.put()
        
        clearCache(blog)

        if existed:
            self.redirect('/' + blog.slug + '/admin')
        else:
            self.redirect('/' + blog.slug + '/admin/author/')


class AuthorsController(AdminController):
    """ handles viewing all authors for this blog """
    def get(self):

        authors = self.blog.authors.order(model.BlogAuthor.name)

        self.renderTemplate('admin/authors.html', authors=authors, page_title="Admin - Authors", logout_url=self.logout_url)


class AuthorController(AdminController):
    """ handles creating and changing authors """

    FIELDS = {"name": validateRequiredString, "url": validateUrl, "email": validateEmail}

    def get(self, author_slug):

        author = None
        page_title = "Admin - Author"
        if author_slug:
            author = model.BlogAuthor.get_by_id(author_slug, parent=self.blog.key)
            if not author:
                return self.renderError(404)
            page_title += " - " + author.name

        form_data, errors = self.errorsFromSession()

        self.renderTemplate('admin/author.html', author=author, form_data=form_data, errors=errors, page_title=page_title, logout_url=self.logout_url)

    def post(self, author_slug):

        blog = self.blog
        author = None
        if author_slug:
            author = model.BlogAuthor.get_by_id(author_slug, parent=blog.key)
            if not author:
                return self.renderError(404)

        form_data, errors, valid_data = self.validate()

        if errors:
            return self.redisplay(form_data, errors, self.blog_url + '/admin/author/' + author_slug)

        name = valid_data["name"]
        slug = model.makeSlug(name, blog, model.BlogAuthor, author)
        if author:
            # if the name is different, remake the entity since the key name needs to change
            if name != author.name:
                # get lists of other entities to update (must be outside of transaction since they're a non-ancestor query)
                posts = list(author.posts)
                comments = list(author.comments)
                # update all the posts and comments referencing the author at the same time that a new author object is created
                def author_transaction(author, slug, blog, ref_lists):
                    # re-create the author object
                    author = model.makeNew(author, id=slug, parent=blog.key, use_transaction=False) # no nested transactions
                    # update the others to reference the new object
                    for ref_list in ref_lists:
                        new_objects = []
                        for ref_object in ref_list:
                            ref_object.author = author
                            new_objects.append(ref_object)
                        model.db.put(new_objects)
                    return author
                author = model.db.run_in_transaction(author_transaction, author, slug, blog, [posts, comments])
            author.populate(**valid_data)
        else:
            author = model.BlogAuthor(id=slug, parent=blog.key, **valid_data)

        author.put()
        
        memcache.delete_multi(getCacheKeys(blog))

        if blog.authors.count() > 1:
            self.redirect(self.blog_url + '/admin/authors')

        else:
            self.redirect(self.blog_url + '/admin')


class PostsController(AdminController):
    """ handles viewing all posts for this blog """
    def get(self):

        blog = self.blog

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

            blog_posts = blog.posts.order(-model.BlogPost.timestamp)
            posts_per_page = blog.posts_per_page

            last_page = (blog_posts.count() - 1) / posts_per_page
            if last_page < 0:
                last_page = 0

            posts = blog_posts.fetch(posts_per_page, offset=page * posts_per_page)

        self.renderTemplate('admin/posts.html', page=page, last_page=last_page, posts=posts,
                            page_title="Admin - Posts", logout_url=self.logout_url)

    def post(self):

        post_slug = self.request.get("post")
        if post_slug:
            # this is a request to delete this post
            post = model.BlogPost.get_by_id(post_slug, parent=self.blog.key)
            if post:
                # delete all the post's comments first
                if post.comments.count() > 0:
                    model.db.delete(list(post.comments))
                # then the post itself
                post.key.delete()
                clearCache(self.blog)
            else:
                return self.renderError(404)

        self.redirect(self.blog_url + '/admin/posts')


class PostController(AdminController):
    """ handles editing and publishing posts """

    FIELDS = {"title": validateRequiredString, "slug_choice": validateRequiredString, "slug": validateString,
        "author": validateRequiredString, "body": validateText, "tags": validateString,
        "timestamp_choice": validateRequiredString, "timestamp": validateDT, "published": validateBool}


    def get(self, post_slug):

        post = None
        if post_slug:
            post = model.BlogPost.get_by_id(post_slug, parent=self.blog.key)
            if not post:
                return self.renderError(404)

        form_data, errors = self.errorsFromSession()

        self.renderTemplate('admin/post.html', post=post, form_data=form_data, errors=errors, page_title="Admin - Post", logout_url=self.logout_url)

    def post(self, post_slug):

        blog = self.blog
        post = None
        if post_slug:
            post = model.BlogPost.get_by_id(post_slug, parent=blog.key)
            if not post:
                return self.renderError(404)

        form_data, errors, valid_data = self.validate()

        if "slug_choice" not in errors and "slug" not in errors:
            slug_choice = valid_data["slug_choice"]
            if slug_choice == "custom":
                slug = valid_data["slug"]
                if slug and "/" not in slug:
                    # check to make sure that there isn't already another post with this slug
                    existing = model.BlogPost.get_by_id(slug, parent=blog.key)
                    if existing and (not post or existing.key != post.key):
                        errors["slug_exists"] = True
                else:
                    errors["slug"] = True

        if "author" not in errors:
            author = model.BlogAuthor.get_by_id(valid_data["author"], parent=blog.key)
            if author:
                valid_data["author"] = author.key
            else:
                errors["author"] = True

        now = datetime.utcnow()
        if "timestamp_choice" not in errors:
            if valid_data["timestamp_choice"] == "now":
                valid_data["timestamp"] = now
            elif not valid_data.get("timestamp"):
                errors["timestamp"] = True

        if errors:
            return self.redisplay(form_data, errors, self.blog_url + '/admin/post/' + post_slug)

        if slug_choice == "auto":
            slug = model.makeSlug(valid_data["title"], blog, model.BlogPost, post)

        # turn tag strings into keys
        tag_keys = []
        if valid_data["tags"]:
            new_tags = []
            for tag_string in valid_data["tags"].split(","):
                tag_string = tag_string.strip()
                if tag_string:
                    tag_slug = model.slugify(tag_string)
                    tag = model.BlogTag.get_by_id(tag_slug, parent=blog.key)
                    if tag:
                        tag_keys.append(tag.key)
                    else:
                        tag_slug = model.makeSlug(tag_string, blog, model.BlogTag)
                        tag = model.BlogTag(id=tag_slug, name=tag_string, parent=blog.key)
                        new_tags.append(tag)
            if new_tags:
                ndb.put_multi(new_tags)
                tag_keys.extend([tag.key for tag in new_tags])
        valid_data["tag_keys"] = tag_keys

        # don't want to attach these temporary choices to the model
        del valid_data["slug"]
        del valid_data["slug_choice"]
        del valid_data["tags"]
        del valid_data["timestamp_choice"]

        was_published = False
        if post:
            was_published = post.published

            # if the slug is different, remake the entities since the key name needs to change
            if slug != post.slug:
                post = model.makeNew(post, id=slug, parent=blog.key)
            post.populate(**valid_data)
        else:
            post = model.BlogPost(id=slug, parent=blog.key, **valid_data)

        post.put()

        # send them back to the admin list of posts if it's not published or to the actual post if it is
        if post.published:
            cache_keys = getCacheKeys(blog)
            memcache.delete_multi(cache_keys)
            datastore_keys = getDatastoreKeys(blog)
            if post.timestamp > now:
                # post is in the future, so set the expires on these to just after it's available
                html_caches = ndb.get_multi(datastore_keys, use_memcache=False)
                new_html_caches = []
                diff = int((post.timestamp - now).total_seconds())
                for html_cache in html_caches:
                    if html_cache:
                        html_cache.expires = diff
                        new_html_caches.append(html_cache)
                if new_html_caches:
                    ndb.put_multi(new_html_caches)
            else:
                # post is published in the past so just delete everything
                ndb.delete_multi(datastore_keys)
            self.redirect(self.blog_url + '/post/' + post.slug)
        else:
            if was_published:
                clearCache(blog)

            if self.request.get("preview"):
                self.redirect(self.blog_url + '/admin/preview/' + post.slug)
            else:
                self.redirect(self.blog_url + '/admin/posts')


class PreviewController(AdminController):
    """ handles showing an admin-only preview of a post """

    def get(self, post_slug):

        post = None
        if post_slug:
            post = model.BlogPost.get_by_id(post_slug, parent=self.blog.key)
        
        if post:
            self.renderTemplate('admin/preview.html', post=post, logout_url=self.logout_url)
        else:
            self.renderError(404)


class CommentsController(AdminController):
    """ handles moderating comments """

    def get(self):

        comments = self.blog.comments.filter(model.BlogComment.approved == False)

        self.renderTemplate('admin/comments.html', comments=comments, page_title="Admin - Comments", logout_url=self.logout_url)

    def post(self):
        
        comment_key = self.request.get("comment")
        if comment_key:
            # delete this individual comment
            comment = None
            try:
                comment = ndb.Key(urlsafe=comment_key).get()
            except:
                pass
            
            if not comment:
                return self.renderError(404)
            else:
                block = self.request.get("block")
                if block:
                    # also block the IP address
                    blog = self.blog
                    if comment.ip_address and comment.ip_address not in blog.blocklist:
                        blog.blocklist.append(comment.ip_address)
                        blog.put()

                if block or self.request.get("delete"):
                    comment.key.delete()
                    # return them to the post they were viewing if this was deleted from a post page
                    post_slug = self.request.get("post")
                    if post_slug:
                        return self.redirect(self.blog_url + '/post/' + post_slug + '#comments')

                else:
                    if comment.linkback:
                        # just approve this one
                        comments = [comment]
                    else:
                        # approve all the comments with the submitted email address here
                        comments = self.blog.comments.filter(model.BlogComment.email == comment.email)

                    for comment in comments:
                        comment.approved = True
                        comment.put()
                        post_path = self.blog_url + '/post/' + comment.post.slug
                        memcache.delete(post_path)

        self.redirect(self.blog_url + '/admin/comments')


class ImagesController(AdminController):
    """ handles managing images """

    def get(self):

        blog = self.blog

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

            images = list(blog_images.order(-model.BlogImage.timestamp).fetch(images_per_page, offset=page * images_per_page))

        if self.request.get("json"):
            self.renderJSON({'page': page, 'last_page': last_page, 'images': [img.url for img in images]})
        else:
            blob_infos = []
            if images:
                info_keys = [img.blob for img in images]
                blob_infos = blobstore.BlobInfo.get(info_keys)
            self.renderTemplate('admin/images.html', page=page, last_page=last_page, images=images, blob_infos=blob_infos,
                                page_title="Admin - Images", logout_url=self.logout_url)

    def post(self):

        image_id = self.request.get("image")
        if image_id:
            image = None
            try:
                image = model.BlogImage.get_by_id(int(image_id), parent=self.blog.key)
            except:
                pass

            if image:
                # delete children first
                blobstore.delete(image.blob)
                # then this one
                image.key.delete()
            else:
                return self.renderError(404)

        self.redirect(self.blog_url + '/admin/images')


class ImageController(AdminController, blobstore_handlers.BlobstoreUploadHandler):
    """ handles uploading images """

    def get(self):

        if self.request.get("json"):
            upload_url = blobstore.create_upload_url(self.blog_url + '/admin/image')
            self.renderJSON({'url': upload_url})
        else:
            page_title = "Admin - Upload an Image"

            form_data, errors = self.errorsFromSession()

            self.renderTemplate('admin/image.html', errors=errors, page_title=page_title, logout_url=self.logout_url)

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
            return self.redisplay({}, errors, self.blog_url + '/admin/image')

        image = model.BlogImage(parent=self.blog.key, blob=blob_info.key())
        image.url = images.get_serving_url(blob_info)
        image.put()

        self.redirect(self.blog_url + '/admin/images')


class MigrateController(AdminController):
    """ handles running any migrations """

    def get(self):
        return self.renderError(405)

    def post(self):

        # migrate any images that don't have a url
        new_images = []
        for image in self.blog.images:
            if not image.url:
                image.url = images.get_serving_url(image.blob)
                new_images.append(image)
        if new_images:
            model.db.put(new_images)

        self.redirect(self.blog_url + '/admin')


def getCacheKeys(blog):
    """ lists keys for anything with the blog or its descendents that might be cached """
    url = '/' + blog.slug
    keys = [url, url + '/contact', url + '/feed']
    for post in blog.published_posts:
        keys.append(url + '/post/' + post.slug)

    blog_pages = (blog.published_posts.count() - 1) / blog.posts_per_page
    if blog_pages < 0:
        blog_pages = 0

    for page in range(blog_pages):
        keys.append(url + 'page=' + str(page + 1))

    for author in blog.authors:
        author_url = (url + '/author/' + author.slug)
        keys.append(author_url)

        author_pages = (author.published_posts.count() - 1) / blog.posts_per_page
        if author_pages < 0:
            author_pages = 0

        for page in range(author_pages):
            keys.append(author_url + 'page=' + str(page + 1))

    return keys


def getDatastoreKeys(blog):
    url = '/' + blog.slug
    string_keys = [url + '/feed']
    return [model.ndb.Key('HTMLCache', key) for key in string_keys]


def clearCache(blog):
    cache_keys = getCacheKeys(blog)
    memcache.delete_multi(cache_keys)
    datastore_keys = getDatastoreKeys(blog)
    ndb.delete_multi(datastore_keys)
