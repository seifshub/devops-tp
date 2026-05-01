import unittest
from app import app

class FlaskAppTestCase(unittest.TestCase):

    def setUp(self):
        # Creates a test client before each test
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

    def test_health_endpoint(self):
        response = self.app.get('/health')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'UP')

    def test_metrics_endpoint(self):
        response = self.app.get('/metrics')
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()


