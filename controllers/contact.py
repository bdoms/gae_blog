from base import FormController, cacheAndRender

from gae_blog.lib.gae_validators import validateString, validateRequiredString, validateRequiredText, validateRequiredEmail
from gae_blog import model


class ContactController(FormController):
    """ handles request for the contact page of the site """

    FIELDS = {"author": validateRequiredString, "email": validateRequiredEmail, "subject": validateString, "body": validateRequiredText}

    @cacheAndRender(skip_check=lambda controller: 'errors' in controller.session)
    def get(self):

        blog = self.blog

        if not blog or not blog.contact:
            return self.renderError(403)

        sent = self.session.pop("blog_contact_sent", False)

        authors = [author for author in blog.authors if author.email]

        form_data, errors = self.errorsFromSession()

        self.renderTemplate('contact.html', sent=sent, authors=authors, form_data=form_data, errors=errors, page_title="Contact")

    def post(self, sent=False):

        blog = self.blog
        if blog and blog.contact and blog.admin_email:
            
            bot = self.botProtection('/contact')
            if bot:
                self.session["blog_contact_sent"] = True
                return

            # validation and handling
            form_data, errors, valid_data = self.validate()

            if "author" not in errors:
                authors = []
                if valid_data["author"] == "all":
                    authors = [author for author in blog.authors if author.email]
                else:
                    author = model.BlogAuthor.get_by_id(valid_data["author"], parent=blog.key)
                    if author and author.email:
                        authors = [author]

                if not authors:
                    errors["author"] = True

            if errors:
                return self.redisplay(form_data, errors, self.blog_url + '/contact')

            if blog.title:
                subject = blog.title + " - Contact Form Message: " + valid_data["subject"]
            else:
                subject = "Blog - Contact Form Message: " + valid_data["subject"]

            for author in authors:
                self.deferEmail(author.name + " <" + author.email + ">", subject, valid_data["body"], valid_data["email"])

            self.session["blog_contact_sent"] = True
            self.redirect(self.blog_url + '/contact')
        else:
            self.renderError(403)
