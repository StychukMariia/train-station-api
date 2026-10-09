from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from train_station.models import Train, TrainType
from train_station.serializers import (
    TrainSerializer,
    TrainListSerializer,
)

TRAIN_URL = reverse("train_station:train-list")


def sample_train_type(**params):
    defaults = {"name": "Electric"}
    defaults.update(params)
    return TrainType.objects.create(**defaults)


def sample_train(**params):
    train_type = params.pop("train_type", None)

    if not train_type:
        train_type = sample_train_type()

    defaults = {
        "name": "Intercity+",
        "cargo_num": 8,
        "places_in_cargo": 50,
        "train_type": train_type,
    }
    defaults.update(params)
    return Train.objects.create(**defaults)


class TrainModelTests(APITestCase):
    def setUp(self):
        self.train = sample_train()

    def test_train_str(self):
        self.assertEqual(str(self.train), "Intercity+")


class UnauthenticatedTrainApiTests(APITestCase):
    def test_auth_required_for_list(self):
        response = self.client.get(TRAIN_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_auth_required_for_create(self):
        train_type = sample_train_type()
        data = {
            "name": "Express",
            "cargo_num": 5,
            "places_in_cargo": 40,
            "train_type": train_type.id,
        }
        response = self.client.post(TRAIN_URL, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedTrainApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="testuser@test.com", password="testpassword123"
        )
        self.client.force_authenticate(user=self.user)

        self.train_type1 = sample_train_type(name="Electric")
        self.train_type2 = sample_train_type(name="Diesel")

        self.train1 = sample_train(name="Hyundai", train_type=self.train_type1)
        self.train2 = sample_train(name="Skoda", train_type=self.train_type2)

    def test_regular_user_can_list_trains(self):
        response = self.client.get(TRAIN_URL)
        trains = Train.objects.all().select_related("train_type")
        serializer = TrainListSerializer(trains, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_regular_user_can_retrieve_train_detail(self):
        detail_url = reverse("train_station:train-detail", args=[self.train1.id])
        response = self.client.get(detail_url)
        serializer = TrainSerializer(self.train1)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_filter_trains_by_name(self):
        response = self.client.get(TRAIN_URL, {"name": "Hyun"})
        serializer = TrainListSerializer(
            Train.objects.filter(name__icontains="Hyun"), many=True
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_filter_trains_by_train_type(self):
        response = self.client.get(TRAIN_URL, {"train_type": self.train_type1.id})
        serializer = TrainListSerializer(
            Train.objects.filter(train_type=self.train_type1), many=True
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_regular_user_cannot_create_train(self):
        data = {
            "name": "Express",
            "cargo_num": 6,
            "places_in_cargo": 45,
            "train_type": self.train_type1.id,
        }
        response = self.client.post(TRAIN_URL, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminTrainApiTests(APITestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            email="adminuser@admin.admin", password="adminpassword123"
        )
        self.client.force_authenticate(user=self.admin)
        self.train_type = sample_train_type()

    def test_admin_can_create_train(self):
        data = {
            "name": "Sapsan",
            "cargo_num": 10,
            "places_in_cargo": 60,
            "train_type_id": self.train_type.id,
        }
        response = self.client.post(TRAIN_URL, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Train.objects.filter(name="Sapsan").exists())
