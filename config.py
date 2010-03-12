# this is the place for all the application configuration constants

# templates
import os

TEMPLATES_DIR = 'templates'
TEMPLATES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), TEMPLATES_DIR)


# url routes
from controllers import admin, index, post

ROUTES = [('/blog', index.IndexController),
          ('/blog/post/(.*)', post.PostController),
          ('/blog/admin', admin.AdminController),
          ('/blog/admin/post/(.*)', admin.PostController),
          ('/blog/admin/posts', admin.PostsController),
          ('/blog/admin/comments', admin.CommentsController)
         ]
