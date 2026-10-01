from datetime import date
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from train_station.models import Station, Route, TrainType, Train, Crew, Journey
from train_station.serializers import JourneyListSerializer, JourneyDetailSerializer

JOURNEY_URL = reverse("train_station:journey-list")


def sample_station(**params):
    defaults = {"name": "Kyiv", "latitude": 50.4, "longitude": 30.5}
    defaults.update(params)
    return Station.objects.create(**defaults)


def sample_route(**params):
    source = params.pop("source", None)
    destination = params.pop("destination", None)
    if not source:
        source = sample_station(name="Kyiv")
    if not destination:
        destination = sample_station(name="Lviv", latitude=49.8, longitude=24.0)
    defaults = {"source": source, "destination": destination, "distance": 500}
    defaults.update(params)
    return Route.objects.create(**defaults)


def sample_train_type(**params):
    defaults = {"name": "Electric"}
    defaults.update(params)
    return TrainType.objects.create(**defaults)


def sample_train(**params):
    train_type = params.pop("train_type", None)
    if not train_type:
        train_type = sample_train_type()
    defaults = {
        "name": "Intercity",
        "cargo_num": 5,
        "place_in_cargo": 40,
        "train_type": train_type,
    }
    defaults.update(params)
    return Train.objects.create(**defaults)


def sample_crew(**params):
    defaults = {"first_name": "Ivan", "last_name": "Franko"}
    defaults.update(params)
    return Crew.objects.create(**defaults)


def sample_journey(**params):
    route = params.pop("route", None)
    train = params.pop("train", None)
    if not route:
        route = sample_route()
    if not train:
        train = sample_train()
    defaults = {
        "route": route,
        "train": train,
        "departure_date": "2026-10-15",
        "arrival_date": "2026-10-15",
    }
    defaults.update(params)
    journey = Journey.objects.create(**defaults)
    crew = sample_crew()
    journey.crews.add(crew)
    return journey


class JourneyModelTests(APITestCase):
    def setUp(self):
        self.journey = sample_journey()

    def test_journey_str(self):
        expected_str = (
            f"{self.journey.train.name} "
            f"({self.journey.departure_date} - {self.journey.arrival_date})"
        )
        self.assertEqual(str(self.journey), expected_str)


class UnauthenticatedJourneyApiTests(APITestCase):
    def test_auth_required_for_list(self):
        response = self.client.get(JOURNEY_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedJourneyApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="testuser@test.com", password="testpassword123"
        )
        self.client.force_authenticate(user=self.user)
        self.journey1 = sample_journey(departure_date="2026-10-15", arrival_date="2026-10-15")
        self.journey2 = sample_journey(departure_date="2026-10-20", arrival_date="2026-10-20")

    def test_regular_user_can_list_journeys(self):
        response = self.client.get(JOURNEY_URL)
        journeys = Journey.objects.all()
        serializer = JourneyListSerializer(journeys, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_regular_user_can_retrieve_journey_detail(self):
        detail_url = reverse("train_station:journey-detail", args=[self.journey1.id])
        response = self.client.get(detail_url)
        serializer = JourneyDetailSerializer(self.journey1)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_filter_journeys_by_date(self):
        response = self.client.get(JOURNEY_URL, {"departure_date": "2026-10-15"})
        serializer = JourneyListSerializer(
            Journey.objects.filter(departure_date=date(2026, 10, 15)), many=True
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)


class AdminJourneyApiTests(APITestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            email="adminuser@admin.admin", password="adminpassword123"
        )
        self.client.force_authenticate(user=self.admin)
        self.route = sample_route()
        self.train = sample_train()
        self.crew = sample_crew()

    def test_admin_can_create_journey(self):
        data = {
            "route": self.route.id,
            "train": self.train.id,
            "departure_date": "2026-11-01",
            "arrival_date": "2026-11-01",
            "crews": [self.crew.id],
        }
        response = self.client.post(JOURNEY_URL, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Journey.objects.filter(departure_date="2026-11-01").exists())
