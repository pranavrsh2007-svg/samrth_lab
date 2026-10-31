import os
import shutil
import tempfile

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

def is_serverless_env():
    """Detects if running in Vercel serverless environment or read-only container."""
    return bool(
        os.environ.get('VERCEL') == '1' or
        os.environ.get('VERCEL_ENV') is not None or
        BASE_DIR.startswith('/var/task')
    )

def resolve_upload_folder():
    """Resolves an appropriate, writable upload directory."""
    if 'UPLOAD_FOLDER' in os.environ:
        return os.environ['UPLOAD_FOLDER']
    if is_serverless_env() or not os.access(BASE_DIR, os.W_OK):
        return os.path.join(tempfile.gettempdir(), 'uploads')
    return os.path.join(BASE_DIR, 'uploads')

def resolve_database_path():
    """Resolves database file location, ensuring serverless environments use /tmp with pre-seeded data."""
    if 'DATABASE_PATH' in os.environ:
        return os.environ['DATABASE_PATH']
    base_db = os.path.join(BASE_DIR, 'labfix.db')
    if is_serverless_env() or not os.access(BASE_DIR, os.W_OK):
        tmp_db = os.path.join(tempfile.gettempdir(), 'labfix.db')
        if not os.path.exists(tmp_db) and os.path.exists(base_db):
            try:
                shutil.copy2(base_db, tmp_db)
            except Exception:
                pass
        return tmp_db
    return base_db

IS_VERCEL = is_serverless_env()

class Config:
    BASE_DIR = BASE_DIR
    IS_VERCEL = is_serverless_env()
    SECRET_KEY = os.environ.get('SECRET_KEY', 'labfix-super-secret-key-prod-2026')
    DATABASE = resolve_database_path()
    UPLOAD_FOLDER = resolve_upload_folder()
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max image upload
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    # Application Base URL (used for generated links and SMS alert dispatch)
    APP_URL = os.environ.get('APP_URL', 'http://localhost:5000')

    # Cloudinary Persistent Storage Configuration
    CLOUDINARY_URL = os.environ.get('CLOUDINARY_URL', '')
    CLOUDINARY_CLOUD_NAME = os.environ.get('CLOUDINARY_CLOUD_NAME', '')
    CLOUDINARY_API_KEY = os.environ.get('CLOUDINARY_API_KEY', '')
    CLOUDINARY_API_SECRET = os.environ.get('CLOUDINARY_API_SECRET', '')

    # Real-World SMS Alert Gateway Configuration
    # Supported: TWILIO, FAST2SMS, or SIMULATED (auto-detected if credentials provided)
    SMS_ENABLED = os.environ.get('SMS_ENABLED', 'True').lower() in ('true', '1')
    SMS_PROVIDER = os.environ.get('SMS_PROVIDER', 'AUTO')  # 'TWILIO', 'FAST2SMS', 'SIMULATED', 'AUTO'
    
    # Twilio API credentials (optional for global real SMS)
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
    TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER', '')

    # Fast2SMS API Key (optional for Indian mobile numbers)
    FAST2SMS_API_KEY = os.environ.get('FAST2SMS_API_KEY', '')

