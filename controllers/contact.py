from google.appengine.api import mail

from base import BaseController

from gae_blog import model
from gae_blog.formencode.validators import UnicodeString, Email

class ContactController(BaseController):
    """ handles request for the contact page of the site """
    def get(self, sent=False):

        blog = self.getBlog()

        if not blog or not blog.contact:
            return self.renderError(403)

        authors = [author for author in blog.authors if author.email]

        return self.renderTemplate('contact.html', sent=sent, authors=authors, page_title="Contact")

    def post(self, sent=False):

        blog = self.getBlog()
        if blog and blog.contact:
            author_key = self.request.get("author")
            email = self.request.get("email")
            subject = self.request.get("subject", "")
            body = self.request.get("body")

            # validation and handling
            email = self.validate(Email(), email, "Email")
            if not email: return

            subject = self.validate(UnicodeString(), subject, "Subject")
            if subject is None: return
            if blog.title:
                subject = blog.title + " - Contact Form Message:" + subject
            else:
                subject = "Blog - Contact Form Message:" + subject

            body = self.validate(UnicodeString(not_empty=True), body, "Message")
            if not body: return

            if author_key == "all":
                authors = [author for author in blog.authors if author.email]
                if not authors:
                    return self.renderError(400)
            else:
                author = model.BlogAuthor.get(author_key)
                if not author or not author.email:
                    return self.renderError(400)
                authors = [author]

            if blog.admin_email:
                for author in authors:
                    mail.send_mail(sender=blog.admin_email, reply_to=email, to=author.name + " <" + author.email + ">", subject=subject, body=body)

        return self.redirect(self.blog_url + '/contact/sent')

