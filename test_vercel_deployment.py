import unittest
import os
import io
import json
import tempfile
from unittest.mock import patch

# Point to temporary test database
TEST_DB = os.path.join(tempfile.gettempdir(), 'test_vercel_labfix.db')

import config
from config import Config, resolve_upload_folder, resolve_database_path
from app import create_app
from database import init_db
from models import Complaint, Computer
from services.storage_service import (
    is_cloudinary_configured,
    save_uploaded_file,
    get_attachment_url
)

class VercelDeploymentTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.path.exists(TEST_DB):
            try:
                os.remove(TEST_DB)
            except Exception:
                pass
        Config.DATABASE = TEST_DB
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False
        with cls.app.app_context():
            init_db()

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(TEST_DB):
            try:
                os.remove(TEST_DB)
            except Exception:
                pass

    def setUp(self):
        self.client = self.app.test_client()

    def test_01_upload_folder_resolution_in_serverless(self):
        """Verify that when VERCEL=1 is set, upload folder defaults to /tmp."""
        with patch.dict(os.environ, {'VERCEL': '1'}, clear=False):
            # Test helper function
            folder = resolve_upload_folder()
            self.assertTrue(folder.startswith(tempfile.gettempdir()))

    def test_02_database_path_resolution_in_serverless(self):
        """Verify that when VERCEL=1 is set, database defaults to /tmp."""
        with patch.dict(os.environ, {'VERCEL': '1'}, clear=False):
            db_path = resolve_database_path()
            self.assertTrue(db_path.startswith(tempfile.gettempdir()))
            self.assertTrue(db_path.endswith('labfix.db'))

    def test_03_create_app_with_readonly_filesystem_simulation(self):
        """Simulate read-only filesystem creating directories to verify create_app does not crash."""
        with patch('os.makedirs', side_effect=OSError(30, "Read-only file system")):
            # create_app should catch OSError and not raise an exception
            test_app = create_app()
            self.assertIsNotNone(test_app)

    def test_04_storage_service_local_fallback(self):
        """Test file save with local/tmp fallback when Cloudinary is not configured."""
        with self.app.app_context():
            fake_image = io.BytesIO(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR...")
            fake_image.filename = "fault_screenshot.png"
            
            identifier = save_uploaded_file(fake_image)
            self.assertIsNotNone(identifier)
            self.assertTrue(identifier.startswith("fault_"))
            self.assertTrue(identifier.endswith(".png"))

            # Check that file exists in upload folder
            upload_path = os.path.join(self.app.config['UPLOAD_FOLDER'], identifier)
            self.assertTrue(os.path.exists(upload_path))
            
            # Clean up
            try:
                os.remove(upload_path)
            except Exception:
                pass

    def test_05_storage_service_cloudinary_mock(self):
        """Test file save when Cloudinary credentials are provided."""
        mock_result = {
            'secure_url': 'https://res.cloudinary.com/testcloud/image/upload/v123456/labfix_complaints/sample.jpg',
            'public_id': 'labfix_complaints/sample'
        }
        with patch.dict(os.environ, {'CLOUDINARY_URL': 'cloudinary://key:secret@testcloud'}):
            self.assertTrue(is_cloudinary_configured())
            with patch('cloudinary.uploader.upload', return_value=mock_result):
                fake_image = io.BytesIO(b"fake image data")
                fake_image.filename = "broken_pc.jpg"
                result_url = save_uploaded_file(fake_image)
                self.assertEqual(result_url, mock_result['secure_url'])

    def test_06_attachment_url_routing(self):
        """Test attachment URL resolution and /uploads route behavior."""
        # Remote URL
        remote_url = "https://res.cloudinary.com/test/image/upload/sample.png"
        self.assertEqual(get_attachment_url(remote_url), remote_url)

        # Local filename
        local_ref = "test_img.png"
        url = get_attachment_url(local_ref)
        self.assertIn("/uploads/test_img.png", url)

        # Test request redirection for remote URL
        res = self.client.get(f"/uploads/{remote_url}")
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.headers.get('Location'), remote_url)

    def test_07_faculty_report_fault_with_upload(self):
        """Test faculty submitting a fault report with an attachment."""
        # Login as faculty
        self.client.post('/login', data={
            'username': 'faculty',
            'password': 'Password@123',
            'role': 'faculty'
        }, follow_redirects=True)

        with self.app.app_context():
            pc = Computer.find_by_id(1)
            self.assertIsNotNone(pc)

        # Submit fault report with attachment
        file_data = (io.BytesIO(b"fake screenshot content"), 'screenshot.png')
        res = self.client.post('/faculty/report-fault', data={
            'computer_id': '1',
            'problem_category': 'Monitor Problem',
            'priority': 'High',
            'description': 'Monitor display flickering with horizontal artifacts during lab hours.',
            'attachment': file_data
        }, content_type='multipart/form-data', follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Fault Ticket Registered', res.data)
        with self.app.app_context():
            complaints = Complaint.get_all(search='horizontal artifacts')
            self.assertTrue(len(complaints) > 0)
            latest = complaints[0]
            self.assertIsNotNone(latest.attachment_filename)
            self.assertTrue(latest.attachment_filename.startswith('fault_'))

    def test_08_vercel_entrypoint_and_config(self):
        """Test api/index.py entrypoint and vercel.json format."""
        # Check vercel.json
        vercel_json_path = os.path.join(os.path.dirname(__file__), 'vercel.json')
        self.assertTrue(os.path.exists(vercel_json_path))
        with open(vercel_json_path, 'r') as f:
            v_conf = json.load(f)
        self.assertEqual(v_conf.get('version'), 2)
        self.assertTrue(any(r.get('destination') == '/api/index' for r in v_conf.get('rewrites', [])))

        # Check api/index.py import
        from api.index import app as vercel_app
        self.assertIsNotNone(vercel_app)
        self.assertEqual(vercel_app.name, 'app')

if __name__ == '__main__':
    unittest.main()
