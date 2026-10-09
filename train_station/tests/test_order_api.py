from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from train_station.models import (
    Station,
    Route,
    TrainType,
    Train,
    Journey,
    Order,
)
from train_station.serializers import OrderListSerializer

ORDER_URL = reverse("train_station:order-list")


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
        "places_in_cargo": 40,
        "train_type": train_type,
    }
    defaults.update(params)
    return Train.objects.create(**defaults)


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
    return Journey.objects.create(**defaults)


def sample_order(user, **params):
    defaults = {}
    defaults.update(params)
    return Order.objects.create(user=user, **defaults)


class UnauthenticatedOrderApiTests(APITestCase):
    def test_auth_required_for_list(self):
        response = self.client.get(ORDER_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedOrderApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="testuser@test.com", password="testpassword123"
        )
        self.other_user = get_user_model().objects.create_user(
            email="otheruser@test.com", password="testpassword123"
        )
        self.client.force_authenticate(user=self.user)

        self.journey = sample_journey()
        self.order1 = sample_order(user=self.user)
        self.order2 = sample_order(user=self.other_user)

    def test_user_can_list_only_their_orders(self):
        response = self.client.get(ORDER_URL)

        orders = Order.objects.filter(user=self.user)
        serializer = OrderListSerializer(orders, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], serializer.data)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.order1.id)

    def test_user_can_create_order_with_tickets(self):
        data = {
            "tickets": [
                {
                    "cargo": 1,
                    "seat": 15,
                    "journey": self.journey.id,
                },
                {
                    "cargo": 1,
                    "seat": 16,
                    "journey": self.journey.id,
                },
            ]
        }
        response = self.client.post(ORDER_URL, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 3)

        created_order = Order.objects.latest("created_at")
        self.assertEqual(created_order.tickets.count(), 2)
        self.assertEqual(created_order.user, self.user)

    def test_cannot_create_order_with_invalid_seat(self):
        data = {
            "tickets": [
                {
                    "cargo": 1,
                    "seat": 999,
                    "journey": self.journey.id,
                }
            ]
        }
        response = self.client.post(ORDER_URL, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
