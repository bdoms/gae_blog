# this is the place for all the application configuration constants

# templates
import os

BLOG_PATH = os.path.dirname(os.path.abspath(__file__))

TEMPLATES_DIR = 'templates'
TEMPLATES_PATH = os.path.join(BLOG_PATH, TEMPLATES_DIR)

# url routes
BLOG_URLS = ['/blog']

from controllers import admin, author, contact, feed, index, post

ROUTES = []

for url in BLOG_URLS:
    ROUTES.extend([(url, index.IndexController),
                   (url + '/feed', feed.FeedController),
                   (url + '/contact/(.*)', contact.ContactController),
                   (url + '/post/(.*)', post.PostController),
                   (url + '/author/(.*)', author.AuthorController),
                   (url + '/admin', admin.AdminController),
                   (url + '/admin/blog/(.*)', admin.BlogController),
                   (url + '/admin/author/(.*)', admin.AuthorController),
                   (url + '/admin/authors', admin.AuthorsController),
                   (url + '/admin/post/(.*)', admin.PostController),
                   (url + '/admin/posts', admin.PostsController),
                   (url + '/admin/preview/(.*)', admin.PreviewController),
                   (url + '/admin/comments', admin.CommentsController),
                   (url + '/admin/image', admin.ImageController),
                   (url + '/admin/images', admin.ImagesController)
                ])

