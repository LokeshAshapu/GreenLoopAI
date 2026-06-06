import os
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile

def validate_image_upload(file):
    """
    Validates uploaded images to protect against:
    - DOS attacks (file size limits)
    - Web shells / malicious scripts disguised as images (extension and content-type checking)
    """
    if not isinstance(file, UploadedFile):
        return

    # 1. Validate File Size (Limit to 5 MB)
    max_size = 5 * 1024 * 1024  # 5 Megabytes
    if file.size > max_size:
        raise ValidationError("File size exceeds the maximum limit of 5MB.")

    # 2. Validate Extension
    valid_extensions = ['.jpg', '.jpeg', '.png', '.webp']
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in valid_extensions:
        raise ValidationError(f"Unsupported file extension. Allowed extensions are: {', '.join(valid_extensions)}")

    # 3. Validate Content-Type
    valid_content_types = ['image/jpeg', 'image/png', 'image/webp']
    if file.content_type not in valid_content_types:
        raise ValidationError("Invalid image content type detected.")
