GAE Blog is a project to provide a bare-bones blogging solution for Google App
Engine that makes no assumptions, and is easy to integrate with existing apps.

It uses and includes a copy of the Mako:

    http://www.makotemplates.org/

Which is covered by the MIT License:

    http://www.opensource.org/licenses/mit-license.php


= Setup for Integrating with Your Project =

In your pre-existing application add this project as a submodule, like so:

    git submodule add git://github.com/bdoms/gaeblog.git gaeblog

Next, you need to initialize and update the submodule to get the data:

    git submodule init
    git submodule update

And then just add this to your app.yaml 'handlers' section:

    - url: /blog.*
      script: gaeblog/blog.py
    - url: /blog/admin.*
      script: gaeblog/blog.py
      login: admin

Now going to /blog on your app will be handled by gaeblog.

You should be good to go!


= Setup for Using As a Parent Project =

If you just want the blog to be the only part of your website, the process is
fairly similar. Just clone (or fork) the repository and make your own app.yaml
file that includes the handlers mentioned above.

