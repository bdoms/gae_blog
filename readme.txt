GAE Blog is a project to provide a bare-bones blogging solution that makes no
assumptions, and is easy to integrate with existing apps.

It uses and includes a copy of the Mako:
    http://www.makotemplates.org/
Which is covered by the MIT License:
    http://www.opensource.org/licenses/mit-license.php)


Setup Development Environment (Linux)
    Download GAE: http://code.google.com/appengine/downloads.html
    Add the extracted path to PATH var with these lines in .bashrc file:
        export PATH=${PATH}:/path/to/google_appengine/
        export PYTHONPATH=${PYTHONPATH}:/path/to/google_appengine/
    Install Python: sudo apt-get install python

Run Development Server
    dev_appserver.py --debug --address=0.0.0.0 gae_blog/

Deploy to Production
    appcfg.py update your_project/

