import unittest

from fastapi.testclient import TestClient

from pastrami import create_app


class TestWebApp(unittest.TestCase):
    def setUp(self):
        self.settings = {
            # Database
            "database": {
                "url": "sqlite:///:memory:",
                "create": True,
                "echo": False,
                "encrypted": True,
            },
            # API frontend stuff
            "contact": {
                "name": "Average Joe",
                "url": "http://0.0.0.0:8080/",
                "email": "averagejoe@example.com",
            },
            # UI,
            "docs": False,
            # Text
            "dayspan": 1,
            "maxlength": 10,
        }

        self.app = create_app(settings=self.settings)

    def test_frontend_methods(self):
        with TestClient(self.app) as client:
            response = client.get("/")

            self.assertEqual(response.status_code, 200)
            self.assertIn("<title>Pastrami</title>", response.text)

    def test_api_methods(self):
        with TestClient(self.app) as client:
            # Create text
            response = client.post("/", json={"content": "FooBar"})
            text = response.json()

            self.assertEqual(response.status_code, 200)
            self.assertEqual(text["content"], "FooBar")

            # Create invalid text
            response = client.post("/", json={"content": "Very very long message"})
            self.assertEqual(response.status_code, 406)

            # Get existing
            response = client.get(f"/{text['text_id']}")
            self.assertIn('<pre class="prettyprint linenums:1">FooBar</pre>', response.text)

            # Get non-existing
            response = client.get("f/WRONG")
            self.assertEqual(response.status_code, 404)

            # Delete existing
            response = client.delete(f"/{text['text_id']}")
            self.assertEqual(response.status_code, 204)

            # Delete non existing
            response = client.delete(f"/{text['text_id']}")
            self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)
