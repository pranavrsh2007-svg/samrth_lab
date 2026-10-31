import os
import uuid
import logging
from flask import current_app

logger = logging.getLogger(__name__)

def _is_cloudinary_available():
    try:
        import cloudinary
        import cloudinary.uploader
        return True
    except ImportError:
        return False

def is_cloudinary_configured():
    """Returns True if Cloudinary credentials are provided in environment or app config."""
    if not _is_cloudinary_available():
        return False
    
    if os.environ.get('CLOUDINARY_URL'):
        return True
    
    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME') or (
        current_app.config.get('CLOUDINARY_CLOUD_NAME') if current_app else ''
    )
    api_key = os.environ.get('CLOUDINARY_API_KEY') or (
        current_app.config.get('CLOUDINARY_API_KEY') if current_app else ''
    )
    api_secret = os.environ.get('CLOUDINARY_API_SECRET') or (
        current_app.config.get('CLOUDINARY_API_SECRET') if current_app else ''
    )
    return bool(cloud_name and api_key and api_secret)


def configure_cloudinary():
    """Configures cloudinary client if explicit keys are provided."""
    if not _is_cloudinary_available():
        return False
    import cloudinary

    if os.environ.get('CLOUDINARY_URL'):
        return True
    
    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME') or (
        current_app.config.get('CLOUDINARY_CLOUD_NAME') if current_app else ''
    )
    api_key = os.environ.get('CLOUDINARY_API_KEY') or (
        current_app.config.get('CLOUDINARY_API_KEY') if current_app else ''
    )
    api_secret = os.environ.get('CLOUDINARY_API_SECRET') or (
        current_app.config.get('CLOUDINARY_API_SECRET') if current_app else ''
    )
    
    if cloud_name and api_key and api_secret:
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True
        )
        return True
    return False


def save_uploaded_file(file, folder="labfix_complaints"):
    """
    Saves an uploaded file either to Cloudinary (if configured) or local/tmp UPLOAD_FOLDER.
    Returns:
        identifier (str): Cloudinary secure URL or local unique filename.
    """
    if not file or not getattr(file, 'filename', None):
        return None

    filename = file.filename
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'jpg'
    unique_name = f"fault_{uuid.uuid4().hex[:12]}.{ext}"

    # Try Cloudinary if configured
    if is_cloudinary_configured():
        try:
            import cloudinary.uploader
            configure_cloudinary()
            upload_result = cloudinary.uploader.upload(
                file,
                folder=folder,
                resource_type="auto",
                public_id=f"fault_{uuid.uuid4().hex[:12]}"
            )
            secure_url = upload_result.get('secure_url')
            if secure_url:
                logger.info(f"File uploaded to Cloudinary successfully: {secure_url}")
                return secure_url
        except Exception as e:
            logger.error(f"Cloudinary upload failed, falling back to local/tmp storage: {e}")
            try:
                file.seek(0)
            except Exception:
                pass

    # Local / Temporary storage fallback
    upload_folder = current_app.config.get('UPLOAD_FOLDER') if current_app else None
    if not upload_folder:
        import tempfile
        upload_folder = os.path.join(tempfile.gettempdir(), 'uploads')

    try:
        os.makedirs(upload_folder, exist_ok=True)
    except OSError as e:
        logger.warning(f"Could not create upload directory {upload_folder}: {e}")
        import tempfile
        upload_folder = tempfile.gettempdir()

    upload_path = os.path.join(upload_folder, unique_name)
    try:
        if hasattr(file, 'save'):
            file.save(upload_path)
        elif hasattr(file, 'read'):
            with open(upload_path, 'wb') as f:
                f.write(file.read())
        else:
            with open(upload_path, 'wb') as f:
                f.write(file)
        logger.info(f"File saved to storage: {upload_path}")
        return unique_name
    except Exception as e:
        logger.error(f"Failed to save file to storage {upload_path}: {e}")
        return None


def get_attachment_url(identifier):
    """Returns a viewable/clickable URL for an attachment identifier."""
    if not identifier:
        return ''
    if identifier.startswith('http://') or identifier.startswith('https://'):
        return identifier
    from flask import url_for
    try:
        return url_for('uploaded_file', filename=identifier)
    except Exception:
        return f"/uploads/{identifier}"
