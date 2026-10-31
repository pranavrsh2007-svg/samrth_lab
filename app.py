import os
from flask import Flask, render_template, redirect, url_for, session, send_from_directory, g
from config import Config
from database import init_db, close_db, query_db
from models import User, Notification
from routes.auth import auth_bp
from routes.hod import hod_bp
from routes.faculty import faculty_bp
from routes.technician import technician_bp
from routes.inventory import inventory_bp
from routes.api import api_bp
from services.auth_service import get_current_user

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure upload directory exists safely without crashing if filesystem is read-only
    upload_folder = app.config.get('UPLOAD_FOLDER')
    if upload_folder:
        try:
            os.makedirs(upload_folder, exist_ok=True)
        except OSError:
            pass

    # Ensure database schema is initialized and seeded (for WSGI/Gunicorn and local runs)
    with app.app_context():
        try:
            init_db()
        except Exception as e:
            app.logger.warning(f"Database initialization notice: {e}")

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(hod_bp)
    app.register_blueprint(faculty_bp)
    app.register_blueprint(technician_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(api_bp)

    # Teardown database connection
    app.teardown_appcontext(close_db)

    # Root route
    @app.route('/')
    def index():
        if 'user_id' in session:
            role = session.get('role')
            if role == 'hod':
                return redirect(url_for('hod.dashboard'))
            elif role == 'faculty':
                return redirect(url_for('faculty.dashboard'))
            elif role == 'technician':
                return redirect(url_for('technician.dashboard'))
        return redirect(url_for('auth.login'))

    # Serve uploaded images (supports local files and redirects for remote persistent storage)
    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        if filename.startswith('http://') or filename.startswith('https://'):
            return redirect(filename)
        if filename.startswith('http:/'):
            return redirect(filename.replace('http:/', 'http://', 1))
        if filename.startswith('https:/'):
            return redirect(filename.replace('https:/', 'https://', 1))

        upload_folder = app.config.get('UPLOAD_FOLDER')
        if not upload_folder or not os.path.exists(os.path.join(upload_folder, filename)):
            import tempfile
            tmp_fallback = os.path.join(tempfile.gettempdir(), filename)
            if os.path.exists(tmp_fallback):
                return send_from_directory(tempfile.gettempdir(), filename)
            return render_template('errors/404.html'), 404
        return send_from_directory(upload_folder, filename)

    # Global context processor to make current_user and notifications available in all templates
    @app.context_processor
    def inject_global_data():
        user = get_current_user()
        unread_count = 0
        notifications = []
        if user:
            unread_count = Notification.get_unread_count(user.id, user.role)
            notifications = Notification.get_for_user(user.id, user.role, limit=5)
        return {
            'current_user': user,
            'unread_notifications_count': unread_count,
            'recent_notifications': notifications
        }

    # Custom Jinja filters
    @app.template_filter('status_badge_class')
    def status_badge_class(status):
        mapping = {
            'Working': 'badge-success',
            'Repaired': 'badge-primary',
            'Under Repair': 'badge-warning',
            'Fault Reported': 'badge-danger',
            'Decommissioned': 'badge-secondary',
            'Pending': 'badge-warning',
            'Accepted': 'badge-info',
            'In Progress': 'badge-primary',
            'Resolved': 'badge-success',
            'Closed': 'badge-secondary'
        }
        return mapping.get(status, 'badge-light')

    @app.template_filter('priority_badge_class')
    def priority_badge_class(priority):
        mapping = {
            'Critical': 'badge-critical',
            'High': 'badge-danger',
            'Medium': 'badge-warning',
            'Low': 'badge-info'
        }
        return mapping.get(priority, 'badge-light')

    @app.template_filter('attachment_url')
    def attachment_url_filter(filename_or_url):
        if not filename_or_url:
            return ''
        if filename_or_url.startswith('http://') or filename_or_url.startswith('https://'):
            return filename_or_url
        return url_for('uploaded_file', filename=filename_or_url)

    # Error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(500)
    def server_error(e):
        return render_template('errors/500.html'), 500

    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1')
    print("=" * 60)
    print("  LABFIX: Smart Computer Lab Management System")
    print(f"  Server running on http://127.0.0.1:{port}")
    print("  Default credentials:")
    print("    HOD:        hod / Password@123")
    print("    Faculty:    faculty / Password@123")
    print("    Technician: tech / Password@123")
    print("=" * 60)
    app.run(host='0.0.0.0', port=port, debug=debug)
