from io import BytesIO
from PIL import Image

AUTH_HEADERS = {"Authorization": "Bearer test-administrator-credential-only"}
_image = BytesIO()
Image.new("RGB", (2, 2), "white").save(_image, format="JPEG")
JPEG_BYTES = _image.getvalue()
