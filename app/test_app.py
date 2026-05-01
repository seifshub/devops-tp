import unittest
from app import app

class FlaskAppTestCase(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_home_returns_200(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)

    def test_home_contains_message(self):
        response = self.app.get('/')
        data = response.get_json()
        self.assertIn('message', data)
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['version'], '1.0')

    def test_health_endpoint(self):
        response = self.app.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['status'], 'UP')

    def test_metrics_endpoint(self):
        response = self.app.get('/metrics')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'flask_request', response.data)
        self.assertIn('text/plain', response.content_type)

if __name__ == '__main__':
    unittest.main()