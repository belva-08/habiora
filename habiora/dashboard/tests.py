from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from properties.models import Property
from bookings.models import Booking


class AdminStatisticsViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='secret123',
            is_staff=True,
            is_superuser=True,
        )
        self.owner = User.objects.create_user(
            username='owner',
            email='owner@example.com',
            password='secret123',
        )
        self.property = Property.objects.create(
            title='Test property',
            description='desc',
            property_type='appartement',
            price=1000,
            surface_area=50,
            quartier='Centre',
            address='123 test',
            owner=self.owner,
        )
        Booking.objects.create(
            property=self.property,
            tenant=self.owner,
            start_date='2026-10-01',
            end_date='2026-10-05',
            status='confirmed',
        )

    def test_admin_statistics_page_loads(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('dashboard:admin_statistics'))
        self.assertEqual(response.status_code, 200)
