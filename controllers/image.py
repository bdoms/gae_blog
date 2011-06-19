from google.appengine.api import memcache

from base import BaseController

from gae_blog import model


class ImageController(BaseController):
    """ handles requests for images uploaded to the site """
    def get(self, image_name):

        filename, ext = image_name.rsplit(".")

        # special handling for caching images
        image_key = self.request.path
        if self.request.query_string:
            image_key += "?" + self.request.query_string
        image_data = memcache.get(image_key)
        if image_data:
            if "preview" in image_key:
                # the whole image can be contained within one key
                self.response.headers['Content-Type'] = "image/" + ext
                return self.response.out.write(image_data)
            else:
                image_datas = []
                for key in image_data:
                    piece = memcache.get(key)
                    if piece:
                        image_datas.append(piece)
                if len(image_datas) == len(image_data):
                    # all the pieces were present, proceed
                    self.response.headers['Content-Type'] = "image/" + ext
                    return self.response.out.write(''.join(image_datas))

        blog = self.getBlog()

        if blog and image_name:
            image = blog.images.filter("name =", image_name).get()
            if image:
                self.response.headers['Content-Type'] = "image/" + ext
                if self.request.get("preview"):
                    image_data = image.getPreview(blog)
                    memcache.add(image_key, image_data, 86400)
                    return self.response.out.write(image_data)
                else:
                    image_datas = []
                    pieces = []
                    for i, image_data in enumerate(image.image_datas):
                        image_datas.append(image_data.data)
                        key = image_key + str(i)
                        memcache.add(key, image_data.data, 86400)
                        pieces.append(key)
                    memcache.add(image_key, pieces, 86400)
                    return self.response.out.write(''.join(image_datas))

        return self.renderError(404)

