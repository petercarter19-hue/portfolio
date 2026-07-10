import unittest
from app import app

class SlateBoardV2PreviewTests(unittest.TestCase):
    def test_preview_renders_locally(self):
        response = app.test_client().get('/_internal/slate-board-v2', base_url='http://localhost')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Study for the PMP certification', response.data)

if __name__ == '__main__': unittest.main()
