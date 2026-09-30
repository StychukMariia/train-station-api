from django.contrib.auth import get_user_model
from django.urls import reverse, NoReverseMatch
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from train_station.models import Station
from train_station.serializers import StationSerializer

STATION_URL = reverse("train_station:station-list")


class StationModelTests(APITestCase):
    def setUp(self):
        self.station = Station.objects.create(
            name="Kyiv-Pasazhyrskyi",
            latitude=50.4402,
            longitude=30.4883
        )

    def test_station_str(self):
        self.assertEqual(str(self.station), "Kyiv-Pasazhyrskyi")

    def test_station_creation(self):
        station_from_db = Station.objects.get(name="Kyiv-Pasazhyrskyi")
        self.assertEqual(station_from_db.latitude, 50.4402)
        self.assertEqual(station_from_db.longitude, 30.4883)


class UnauthenticatedStationApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required_for_list(self):
        response = self.client.get(STATION_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_auth_required_for_create(self):
        data = {"name": "Odesa", "latitude": 46.4825, "longitude": 30.7233}
        response = self.client.post(STATION_URL, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedStationApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="testuser@test.com", password="testpassword123"
        )
        self.client.force_authenticate(user=self.user)

    def test_regular_user_can_list_stations(self):
        response = self.client.get(STATION_URL)
        stations = Station.objects.all()
        serializer = StationSerializer(stations, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_regular_user_cannot_create_station(self):
        data = {"name": "Kharkiv", "latitude": 49.9935, "longitude": 36.2304}
        response = self.client.post(STATION_URL, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminStationApiTests(APITestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            email="adminuser@admin.admin", password="adminpassword123"
        )
        self.client.force_authenticate(user=self.admin)
        self.station = Station.objects.create(
            name="Lviv", latitude=49.8397, longitude=24.0297
        )

    def test_admin_can_create_station(self):
        data = {"name": "Dnipro", "latitude": 48.4647, "longitude": 35.0462}
        response = self.client.post(STATION_URL, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Station.objects.filter(name="Dnipro").exists())

    def test_retrieve_station_not_allowed(self):
        with self.assertRaises(NoReverseMatch):
            reverse(
                "train_station:station-detail",
                args=[self.station.id]
            )
