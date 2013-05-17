from base import BaseController


class ErrorController(BaseController):
    """ handles any page that falls through the rest of the routes """

    def get(self, invalid_path):

        self.renderError(404)
