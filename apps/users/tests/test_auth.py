from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

User = get_user_model()


class AuthTests(TestCase):
    def test_register(self):
        c = APIClient()
        r = c.post(
            "/api/v1/auth/register/",
            {
                "username": "newuser",
                "email": "n@e.com",
                "password": "StrongPass123!",
            },
            format="json",
        )
        self.assertIn(r.status_code, (200, 201))
