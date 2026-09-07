from django.test import TestCase
from django.urls import reverse


class PasswordResetPageTests(TestCase):
    def test_password_reset_page_uses_django_login_url(self):
        response = self.client.get(reverse('accounts:password_reset'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/accounts/login/"')
        self.assertNotContains(response, 'login.html')

    def test_password_reset_ajax_post_accepts_email(self):
        response = self.client.post(
            reverse('accounts:password_reset'),
            {'email': 'user@example.com'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('success', response.json())
        self.assertIn('message', response.json())
