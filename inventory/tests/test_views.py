from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class InitialViewsTests(TestCase):
    def test_health_endpoint_is_public(self):
        response = self.client.get(reverse("inventory:healthz"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")

    def test_home_requires_login(self):
        response = self.client.get(reverse("inventory:home"))
        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('inventory:home')}",
        )

    def test_authenticated_user_can_open_home(self):
        user = get_user_model().objects.create_user(username="test-user", password="test-password-123")
        self.client.force_login(user)
        response = self.client.get(reverse("inventory:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lab Inventory")
