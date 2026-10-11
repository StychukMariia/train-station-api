from datetime import datetime

from django.db.models import F, Count
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from rest_framework import viewsets, mixins
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated

from train_station.models import (
    Station,
    Route,
    TrainType,
    Train,
    Crew,
    Journey,
    Order,
)
from train_station.permissions import IsAdminOrIfAuthenticatedReadOnly
from train_station.serializers import (
    StationSerializer,
    RouteSerializer,
    TrainTypeSerializer,
    TrainSerializer,
    CrewSerializer,
    JourneySerializer,
    OrderSerializer,
    RouteListSerializer,
    RouteDetailSerializer,
    TrainListSerializer,
    JourneyListSerializer,
    JourneyDetailSerializer,
    OrderListSerializer,
)


class StationViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Station.objects.all()
    serializer_class = StationSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    @extend_schema(
        summary="List all stations",
        description="Returns a list of all available train stations. Publicly accessible for reading.",
        responses={200: StationSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create a new station",
        description="Allows admin users to create a new train station.",
        responses={
            201: StationSerializer,
            400: OpenApiResponse(
                description="Validation error (e.g. invalid latitude/longitude range or duplicate name)."
            ),
            401: OpenApiResponse(
                description="Authentication credentials were not provided."
            ),
            403: OpenApiResponse(
                description="Permission denied (admin rights required)."
            ),
        },
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


class RouteViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Route.objects.all().select_related("source", "destination")
    serializer_class = RouteSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def get_queryset(self):
        source_id_str = self.request.query_params.get("source")
        destination_id_str = self.request.query_params.get("destination")

        queryset = self.queryset

        if source_id_str:
            try:
                queryset = queryset.filter(source_id=int(source_id_str))
            except ValueError:
                raise ValidationError({"source": "A valid integer is required."})

        if destination_id_str:
            try:
                queryset = queryset.filter(destination_id=int(destination_id_str))
            except ValueError:
                raise ValidationError({"destination": "A valid integer is required."})

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return RouteListSerializer

        if self.action == "retrieve":
            return RouteDetailSerializer

        return RouteSerializer

    @extend_schema(
        summary="List and filter routes",
        description="Retrieve routes with optional filtering by source and destination station IDs.",
        parameters=[
            OpenApiParameter(
                name="source",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter routes by source station ID (e.g. ?source=1)",
                required=False,
            ),
            OpenApiParameter(
                name="destination",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter routes by destination station ID (e.g. ?destination=2)",
                required=False,
            ),
        ],
        responses={
            200: RouteListSerializer(many=True),
            400: OpenApiResponse(
                description="Invalid query parameter format (non-integer ID provided)."
            ),
        },
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Get route details",
        description="Retrieve detailed information about a specific route by its ID.",
        responses={
            200: RouteDetailSerializer,
            404: OpenApiResponse(description="Route not found."),
        },
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


class TrainTypeViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = TrainType.objects.all()
    serializer_class = TrainTypeSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


class TrainViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Train.objects.all().select_related("train_type")
    serializer_class = TrainSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def get_queryset(self):
        name = self.request.query_params.get("name")
        train_type_id_str = self.request.query_params.get("train_type")

        queryset = self.queryset

        if name:
            queryset = queryset.filter(name__icontains=name)

        if train_type_id_str:
            try:
                queryset = queryset.filter(train_type_id=int(train_type_id_str))
            except ValueError:
                raise ValidationError({"train_type": "A valid integer is required."})

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return TrainListSerializer

        return TrainSerializer

    @extend_schema(
        summary="List and filter trains",
        description="Retrieve trains with optional filtering by name or train type ID.",
        parameters=[
            OpenApiParameter(
                name="name",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter trains by name (e.g. ?name=Intercity)",
                required=False,
            ),
            OpenApiParameter(
                name="train_type",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter trains by train type ID (e.g. ?train_type=1)",
                required=False,
            ),
        ],
        responses={
            200: TrainListSerializer(many=True),
            400: OpenApiResponse(description="Invalid train_type parameter format."),
        },
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class CrewViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Crew.objects.all()
    serializer_class = CrewSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


class StandardPagination(PageNumberPagination):
    page_size = 10
    max_page_size = 100


class JourneyViewSet(viewsets.ModelViewSet):
    queryset = (
        Journey.objects.all()
        .select_related(
            "route", "route__source", "route__destination", "train", "train__train_type"
        )
        .prefetch_related("crews")
        .annotate(
            tickets_available=(
                F("train__cargo_num") * F("train__places_in_cargo") - Count("tickets")
            )
        )
        .order_by("-departure_time")
    )
    serializer_class = JourneySerializer
    pagination_class = StandardPagination
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def get_queryset(self):
        departure_date = self.request.query_params.get("departure_date")

        queryset = self.queryset

        if departure_date:
            try:
                date = datetime.strptime(departure_date, "%Y-%m-%d").date()
                queryset = queryset.filter(departure_time__date=date)
            except ValueError:
                raise ValidationError(
                    {"departure_date": "Date has wrong format. Use YYYY-MM-DD format."}
                )

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return JourneyListSerializer

        if self.action == "retrieve":
            return JourneyDetailSerializer

        return JourneySerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="departure_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Filter journeys by departure date (format: YYYY-MM-DD)",
                required=False,
            ),
        ],
        responses={
            200: JourneyListSerializer(many=True),
            400: OpenApiResponse(
                description="Invalid date format provided for departure_date query parameter."
            ),
        },
        summary="List and filter journeys",
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class OrderViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Order.objects.prefetch_related(
        "tickets__journey__train__train_type",
        "tickets__journey__route__source",
        "tickets__journey__route__destination",
    ).all()
    serializer_class = OrderSerializer
    pagination_class = StandardPagination
    permission_classes = (IsAuthenticated,)

    def get_serializer_class(self):
        if self.action == "list":
            return OrderListSerializer

        return OrderSerializer

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @extend_schema(
        summary="Create a new order with tickets",
        description="Allows an authenticated user to book tickets for a specific journey. Validates seat availability and handles race conditions.",
        responses={
            201: OrderSerializer,
            400: OpenApiResponse(
                description="Validation error (e.g., seat already booked, invalid range, or empty tickets)."
            ),
            401: OpenApiResponse(
                description="Authentication credentials were not provided."
            ),
        },
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
