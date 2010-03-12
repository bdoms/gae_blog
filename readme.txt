GAE Blog is a project to provide a bare-bones blogging solution that makes no
assumptions, and is easy to integrate with existing apps.

It uses and includes a copy of the Mako:
    http://www.makotemplates.org/
Which is covered by the MIT License:
    http://www.opensource.org/licenses/mit-license.php)

In your pre-existing application, just add this to your app.yaml 'handlers':

- url: /blog.*
  script: gaeblog/blog.py

And you should be good to go!

