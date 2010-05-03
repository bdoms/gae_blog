from base import BaseController

from gae_blog import model

class ImageController(BaseController):
    """ handles requests for images uploaded to the site """
    def get(self, image_name):

        blog = self.getBlog()

        if blog and image_name:
            image = blog.images.filter("name =", image_name).get()
            if image:
                filename, ext = image_name.rsplit(".")
                self.response.headers['Content-Type'] = "image/" + ext
                # TODO: disabled until GAE allows resizing of larger images
                #if self.request.get("preview"):
                #    self.response.out.write(image.preview)
                #else:
                self.response.out.write(image.data)
                return

        return self.renderError(404)

