from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

CREATE_USER_URL = reverse("user:create")
TOKEN_URL = reverse("user:token_obtain_pair")
ME_URL = reverse("user:manage")


def create_user(**params):
    return get_user_model().objects.create_user(**params)


class UnauthenticatedUserApiTests(APITestCase):
    def test_auth_required_for_manage_user(self):
        response = self.client.get(ME_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PublicUserApiTests(APITestCase):
    def test_create_user_success(self):
        payload = {
            "email": "newuser@test.com",
            "password": "testpassword123",
        }
        response = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(email=payload["email"])
        self.assertTrue(user.check_password(payload["password"]))
        self.assertNotIn("password", response.data)

    def test_user_email_already_exists_error(self):
        payload = {"email": "existing@test.com", "password": "password123"}
        create_user(**payload)

        response = self.client.post(CREATE_USER_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_obtain_token_success(self):
        payload = {"email": "tokenuser@test.com", "password": "password123"}
        create_user(**payload)

        response = self.client.post(TOKEN_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)


class PrivateUserApiTests(APITestCase):
    def setUp(self):
        self.user = create_user(
            email="privateuser@test.com", password="password123"
        )
        self.client.force_authenticate(user=self.user)

    def test_retrieve_user_profile_success(self):
        response = self.client.get(ME_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], self.user.email)

    def test_update_user_profile_success(self):
        payload = {
            "email": "updated@test.com",
            "password": "newpassword123",
        }
        response = self.client.put(ME_URL, payload)

        self.user.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.user.email, payload["email"])
        self.assertTrue(self.user.check_password(payload["password"]))
