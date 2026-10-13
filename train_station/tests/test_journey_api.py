from datetime import date
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from train_station.models import Station, Route, TrainType, Train, Crew, Journey
from train_station.serializers import JourneyListSerializer, JourneyDetailSerializer

JOURNEY_URL = reverse("train_station:journey-list")


def sample_station(name="Kyiv", **params):
    defaults = {
        "latitude": 50.4501,
        "longitude": 30.5234,
    }
    defaults.update(params)
    station, _ = Station.objects.get_or_create(name=name, defaults=defaults)
    return station


def sample_route(**params):
    source = sample_station(name="Kyiv")
    destination = sample_station(name="Lviv")
    defaults = {
        "source": source,
        "destination": destination,
        "distance": 500,
    }
    defaults.update(params)

    route, _ = Route.objects.get_or_create(
        source=defaults["source"],
        destination=defaults["destination"],
        defaults={"distance": defaults["distance"]},
    )
    return route


def sample_train_type(name="Electric", **params):
    defaults = {}
    defaults.update(params)
    train_type, _ = TrainType.objects.get_or_create(name=name, defaults=defaults)
    return train_type


def sample_train(name="Intercity", **params):
    train_type = sample_train_type()
    defaults = {
        "cargo_num": 5,
        "places_in_cargo": 40,
        "train_type": train_type,
    }
    defaults.update(params)

    train, _ = Train.objects.get_or_create(name=name, defaults=defaults)
    return train


def sample_crew(**params):
    defaults = {"last_name": "Franko"}
    defaults.update(params)
    first_name = defaults.pop("first_name", "Ivan")
    crew, _ = Crew.objects.get_or_create(first_name=first_name, defaults=defaults)
    return crew


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
        "departure_time": "2026-10-15T10:00:00Z",
        "arrival_time": "2026-10-15T14:00:00Z",
    }
    defaults.update(params)

    journey, _ = Journey.objects.get_or_create(
        route=defaults["route"],
        train=defaults["train"],
        departure_time=defaults["departure_time"],
        defaults={"arrival_time": defaults["arrival_time"]},
    )

    crew = sample_crew()
    journey.crews.add(crew)
    return journey


class JourneyModelTests(APITestCase):
    def setUp(self):
        self.journey = sample_journey()

    def test_journey_str(self):
        expected_str = (
            f"{self.journey.train.name} "
            f"({self.journey.departure_time} - {self.journey.arrival_time})"
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
        self.journey1 = sample_journey(
            departure_time="2026-10-15T10:00:00Z", arrival_time="2026-10-15T14:00:00Z"
        )
        self.journey2 = sample_journey(
            departure_time="2026-10-20T10:00:00Z", arrival_time="2026-10-20T14:00:00Z"
        )

    def test_regular_user_can_list_journeys(self):
        response = self.client.get(JOURNEY_URL)
        journeys = Journey.objects.all().order_by("-departure_time")
        serializer = JourneyListSerializer(journeys, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], serializer.data)

    def test_regular_user_can_retrieve_journey_detail(self):
        detail_url = reverse("train_station:journey-detail", args=[self.journey1.id])
        response = self.client.get(detail_url)
        serializer = JourneyDetailSerializer(self.journey1)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_filter_journeys_by_date(self):
        response = self.client.get(JOURNEY_URL, {"departure_date": "2026-10-15"})
        journeys = Journey.objects.filter(
            departure_time__date=date(2026, 10, 15)
        ).order_by("-departure_time")
        serializer = JourneyListSerializer(journeys, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], serializer.data)


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
            "departure_time": "2026-11-01T08:00:00Z",
            "arrival_time": "2026-11-01T12:00:00Z",
            "crews": [self.crew.id],
        }
        response = self.client.post(JOURNEY_URL, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Journey.objects.filter(departure_time__date="2026-11-01").exists()
        )
