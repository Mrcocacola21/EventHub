from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.events.models import EventCategory

User = get_user_model()


class EventCategoryApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.list_url = reverse("event-category-list")
        cls.organizer = User.objects.create_user(
            email="organizer@example.com",
            password="StrongPass123!",
            role=User.Roles.ORGANIZER,
        )
        cls.admin = User.objects.create_user(
            email="admin@example.com",
            password="StrongPass123!",
            role=User.Roles.ADMIN,
        )
        cls.regular_user = User.objects.create_user(
            email="user@example.com",
            password="StrongPass123!",
        )

    def results(self, response):
        return response.data.get("results", response.data)

    def test_anonymous_can_list_categories(self):
        category = EventCategory.objects.create(name="Music")

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.results(response)[0]["id"], category.id)

    def test_organizer_can_create_category(self):
        self.client.force_authenticate(self.organizer)

        response = self.client.post(
            self.list_url,
            {"name": "Tournaments", "description": "Competitive events"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["slug"], "tournaments")

    def test_admin_can_create_category(self):
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            self.list_url,
            {"name": "Conferences"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_regular_user_cannot_create_category(self):
        self.client.force_authenticate(self.regular_user)

        response = self.client.post(
            self.list_url,
            {"name": "Private"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_search_categories_by_name(self):
        matching = EventCategory.objects.create(name="Music")
        EventCategory.objects.create(name="Sports")

        response = self.client.get(self.list_url, {"search": "Music"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in self.results(response)], [matching.id])

    def test_order_categories_by_name(self):
        second = EventCategory.objects.create(name="Zulu")
        first = EventCategory.objects.create(name="Alpha")

        response = self.client.get(self.list_url, {"ordering": "name"})

        self.assertEqual(
            [item["id"] for item in self.results(response)],
            [first.id, second.id],
        )
