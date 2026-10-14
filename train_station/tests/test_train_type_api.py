from django.contrib.auth import get_user_model
from django.urls import reverse, NoReverseMatch
from rest_framework import status
from rest_framework.test import APITestCase

from train_station.models import TrainType
from train_station.serializers import TrainTypeSerializer

TRAIN_TYPE_URL = reverse("train_station:traintype-list")


class TrainTypeModelTests(APITestCase):
    def setUp(self):
        self.train_type = TrainType.objects.create(name="Electric")

    def test_train_type_str(self):
        self.assertEqual(str(self.train_type), "Electric")


class UnauthenticatedTrainTypeApiTests(APITestCase):
    def test_auth_required_for_list(self):
        response = self.client.get(TRAIN_TYPE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_auth_required_for_create(self):
        data = {"name": "Diesel"}
        response = self.client.post(TRAIN_TYPE_URL, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedTrainTypeApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="testuser@test.com", password="testpassword123"
        )
        self.client.force_authenticate(user=self.user)
        self.train_type = TrainType.objects.create(name="Electric")

    def test_regular_user_can_list_train_types(self):
        response = self.client.get(TRAIN_TYPE_URL)
        train_types = TrainType.objects.all()
        serializer = TrainTypeSerializer(train_types, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_regular_user_cannot_create_train_type(self):
        data = {"name": "Diesel"}
        response = self.client.post(TRAIN_TYPE_URL, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminTrainTypeApiTests(APITestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            email="adminuser@admin.admin", password="adminpassword123"
        )
        self.client.force_authenticate(user=self.admin)
        self.train_type = TrainType.objects.create(name="Electric")

    def test_admin_can_create_train_type(self):
        data = {"name": "Diesel"}
        response = self.client.post(TRAIN_TYPE_URL, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(TrainType.objects.filter(name="Diesel").exists())

    def test_retrieve_train_type_not_allowed(self):
        with self.assertRaises(NoReverseMatch):
            reverse("train_station:traintype-detail", args=[self.train_type.id])
