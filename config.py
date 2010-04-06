# this is the place for all the application configuration constants

# templates
import os

TEMPLATES_DIR = 'templates'
TEMPLATES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), TEMPLATES_DIR)

BLOG_DIR = 'gae_blog'
BLOG_PATH = os.path.dirname(os.path.abspath(__file__))

# url routes
BLOG_URLS = ['/blog']

from controllers import admin, feed, index, post

ROUTES = []

for url in BLOG_URLS:
    ROUTES.extend([(url, index.IndexController),
                   (url + '/feed', feed.FeedController),
                   (url + '/post/(.*)', post.PostController),
                   (url + '/admin', admin.AdminController),
                   (url + '/admin/blog/(.*)', admin.BlogController),
                   (url + '/admin/author/(.*)', admin.AuthorController),
                   (url + '/admin/authors', admin.AuthorsController),
                   (url + '/admin/post/(.*)', admin.PostController),
                   (url + '/admin/posts', admin.PostsController),
                   (url + '/admin/comments', admin.CommentsController)
                ])
