GAE Blog is a project to provide a bare-bones blogging solution that makes no
assumptions, and is easy to integrate with existing apps.

It uses and includes a copy of the Mako:

    http://www.makotemplates.org/

Which is covered by the MIT License:

    http://www.opensource.org/licenses/mit-license.php)


= Setup =

In your pre-existing application add this project as a submodule, like so:

    git submodule add git://github.com/bdoms/gaeblog.git gaeblog

And then just add this to your app.yaml 'handlers' section:

    - url: /blog.*
      script: gaeblog/blog.py

Now going to /blog on your app will be handled by gaeblog.

To update the submodule, just run:

    git submodule update

You should be good to go!

