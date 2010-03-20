GAE Blog is a project to provide a bare-bones blogging solution that makes no
assumptions, and is easy to integrate with existing apps.

It uses and includes a copy of the Mako:

    http://www.makotemplates.org/

Which is covered by the MIT License:

    http://www.opensource.org/licenses/mit-license.php)


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


= Using a Custom Base Template =

You can obviously modify the included base template as much as you want, but in
order to avoid redundancy, if you already have one that you'd like to use all
you have to do is modify the "Base Template" configuration option on the blog
admin page (at /blog/admin) with a path relative to your project (i.e. the
parent directory of the gaeblog folder). For example, if your directory
structure looks like this:

    - your_project
        - gaeblog
        - your_templates
            - your_base_template.html

You would enter "your_templates/your_base_template.html" as the relative path.
However, if you leave that option blank, then the default_base.html file will
be used instead.

