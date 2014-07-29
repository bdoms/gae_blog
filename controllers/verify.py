from base import FormController


class VerifyController(FormController):
    """ creates a token to help verify a form submission """

    def get(self):

        # send along a token so we can verify this request
        referer = self.request.headers.get("referer")
        if not referer or not referer.startswith(self.request.host_url):
            return self.renderError(400)

        url = self.request.get("url")

        self.renderJSON({'token': self.generateToken(url)})
