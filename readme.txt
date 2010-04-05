GAE Blog is a project to provide a bare-bones blogging solution for Google App
Engine that makes no assumptions, and is easy to integrate with existing apps.

It uses and includes a copy of Mako:
    http://www.makotemplates.org/

Which is covered by the MIT License:
    http://www.opensource.org/licenses/mit-license.php


= Setup for Integrating with Your Project =

In your pre-existing application add this project as a submodule, like so:

    git submodule add git://github.com/bdoms/gae_blog.git gae_blog

Next, you need to initialize and update the submodule to get the data:

    git submodule init
    git submodule update

And then just add this to your app.yaml 'handlers' section (note that the admin
URL must come first in order to be secure):

    - url: /blog/admin.*
      script: gae_blog/blog.py
      login: admin
    - url: /blog.*
      script: gae_blog/blog.py

Now going to /blog on your app will be handled by gae_blog.

Go to /blog/admin to configure your blog, post to it, and moderate comments.


= Setup for Using As a Parent Project =

If you just want the blog to be the only part of your website, the process is
fairly similar. Just clone (or fork) the repository and make your own app.yaml
file that includes the handlers mentioned above.


= Managing Multiple Blogs =

If you want to use GAE Blog for multiple blogs within the same project/domain,
you just have to decide on a relative URL for each one ("/blog" by default)
and modify these things:

    * add handlers for it to your app.yaml as mentioned above
    * add it to the BLOG_URLS list in config.py
    * create each blog with its respective URL from /blog/admin


= Using a Custom Base Template =

You can obviously modify the included base template as much as you want, but in
order to avoid redundancy, if you already have a Mako one that you'd like to
use all you have to do is modify the "Base Template" configuration option on
the blog admin page (at /blog/admin) with a path relative to your project (i.e.
the parent directory of the gae_blog folder). For example, if your directory
structure looks like this:

    - your_project
        - gae_blog
        - your_templates
            - your_base_template.html

You would enter "your_templates/your_base_template.html" as the relative path.
However, if you leave that option blank, then the default_base.html file will
be used instead.

