# this is the place for all the application configuration constants

# templates
import os

TEMPLATES_DIR = 'templates'
TEMPLATES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), TEMPLATES_DIR)


# url routes
from controllers import admin, index, post

ROUTES = [('/', index.IndexController),
          ('/post/(.*)', post.PostController),
          ('/admin', admin.AdminController),
          ('/admin/post/(.*)', admin.PostController),
          ('/admin/posts', admin.PostsController),
          ('/admin/comments', admin.CommentsController)
         ]
