from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from train_station.models import Station, Route
from train_station.serializers import (
    RouteListSerializer,
    RouteDetailSerializer,
)

ROUTE_URL = reverse("train_station:route-list")


def sample_station(**params):
    defaults = {
        "name": "Kyiv",
        "latitude": 50.4402,
        "longitude": 30.4883,
    }
    defaults.update(params)
    return Station.objects.create(**defaults)


def sample_route(**params):
    source = params.pop("source", None)
    destination = params.pop("destination", None)

    if not source:
        source = sample_station(
            name="Kyiv", latitude=50.4, longitude=30.5
        )
    if not destination:
        destination = sample_station(
            name="Lviv", latitude=49.8, longitude=24.0
        )

    defaults = {
        "source": source,
        "destination": destination,
        "distance": 500,
    }
    defaults.update(params)
    return Route.objects.create(**defaults)


class RouteModelTests(APITestCase):
    def setUp(self):
        self.route = sample_route()

    def test_route_str(self):
        expected_str = f"{self.route.source} - {self.route.destination}"
        self.assertEqual(str(self.route), expected_str)


class UnauthenticatedRouteApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required_for_list(self):
        response = self.client.get(ROUTE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_auth_required_for_create(self):
        source = sample_station(name="Kyiv")
        destination = sample_station(name="Lviv")
        data = {
            "source": source.id,
            "destination": destination.id,
            "distance": 500,
        }
        response = self.client.post(ROUTE_URL, data)
        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )


class AuthenticatedRouteApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="testuser@test.com",
            password="testpassword123"
        )
        self.client.force_authenticate(user=self.user)
        self.source1 = sample_station(
            name="Kyiv", latitude=50.4, longitude=30.5
        )
        self.destination1 = sample_station(
            name="Lviv", latitude=49.8, longitude=24.0
        )
        self.destination2 = sample_station(
            name="Odesa", latitude=46.4, longitude=30.7
        )

        self.route1 = sample_route(
            source=self.source1,
            destination=self.destination1,
            distance=500
        )
        self.route2 = sample_route(
            source=self.source1,
            destination=self.destination2,
            distance=700
        )

    def test_regular_user_can_list_routes(self):
        response = self.client.get(ROUTE_URL)
        routes = Route.objects.all().select_related(
            "source", "destination"
        )
        serializer = RouteListSerializer(routes, many=True)

        self.assertEqual(
            response.status_code, status.HTTP_200_OK
        )
        self.assertEqual(response.data, serializer.data)

    def test_regular_user_can_retrieve_route_detail(self):
        """Test that authenticated users can view route details."""
        detail_url = reverse("train_station:route-detail", args=[self.route1.id])
        response = self.client.get(detail_url)

        serializer = RouteDetailSerializer(self.route1)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_filter_routes_by_source_and_destination(self):
        response = self.client.get(
            ROUTE_URL,
            {"destination": self.destination1.id}
        )
        serializer = RouteListSerializer(
            Route.objects.filter(destination=self.destination1), many=True
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_regular_user_cannot_create_route(self):
        data = {
            "source": self.source1.id,
            "destination": self.destination2.id,
            "distance": 600,
        }
        response = self.client.post(ROUTE_URL, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminRouteApiTests(APITestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            email="adminuser@admin.admin", password="adminpassword123"
        )
        self.client.force_authenticate(user=self.admin)
        self.source = sample_station(
            name="Kyiv", latitude=50.4, longitude=30.5
        )
        self.destination = sample_station(
            name="Lviv", latitude=49.8, longitude=24.0
        )

    def test_admin_can_create_route(self):
        data = {
            "source": self.source.id,
            "destination": self.destination.id,
            "distance": 500,
        }
        response = self.client.post(ROUTE_URL, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Route.objects.filter(distance=500).exists())
