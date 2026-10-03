from django.contrib.auth import get_user_model
from django.urls import reverse, NoReverseMatch
from rest_framework import status
from rest_framework.test import APITestCase

from train_station.models import Crew
from train_station.serializers import CrewSerializer

CREW_URL = reverse("train_station:crew-list")


class CrewModelTests(APITestCase):
    def setUp(self):
        self.crew = Crew.objects.create(first_name="Ivan", last_name="Franko")

    def test_crew_str(self):
        self.assertEqual(str(self.crew), "Ivan Franko")

    def test_crew_creation(self):
        crew_from_db = Crew.objects.get(first_name="Ivan")
        self.assertEqual(crew_from_db.last_name, "Franko")


class UnauthenticatedCrewApiTests(APITestCase):
    def test_auth_required_for_list(self):
        response = self.client.get(CREW_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_auth_required_for_create(self):
        data = {"first_name": "Taras", "last_name": "Shevchenko"}
        response = self.client.post(CREW_URL, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedCrewApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="testuser@test.com", password="testpassword123"
        )
        self.client.force_authenticate(user=self.user)
        self.crew = Crew.objects.create(first_name="Ivan", last_name="Franko")

    def test_regular_user_can_list_crew(self):
        response = self.client.get(CREW_URL)
        crew_members = Crew.objects.all()
        serializer = CrewSerializer(crew_members, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_regular_user_cannot_create_crew(self):
        data = {"first_name": "Lesia", "last_name": "Ukrainka"}
        response = self.client.post(CREW_URL, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminCrewApiTests(APITestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            email="adminuser@admin.admin", password="adminpassword123"
        )
        self.client.force_authenticate(user=self.admin)
        self.crew = Crew.objects.create(first_name="Ivan", last_name="Franko")

    def test_admin_can_create_crew(self):
        data = {"first_name": "Taras", "last_name": "Shevchenko"}
        response = self.client.post(CREW_URL, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Crew.objects.filter(first_name="Taras", last_name="Shevchenko").exists()
        )

    def test_retrieve_crew_not_allowed(self):
        with self.assertRaises(NoReverseMatch):
            reverse("train_station:crew-detail", args=[self.crew.id])
