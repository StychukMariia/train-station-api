import datetime

from django.db.models import F, Count
from rest_framework import viewsets

from train_station.models import (
    Station,
    Route,
    TrainType,
    Train,
    Crew,
    Journey,
    Order,
)
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


class StationViewSet(viewsets.ModelViewSet):
    queryset = Station.objects.all()
    serializer_class = StationSerializer


class RouteViewSet(viewsets.ModelViewSet):
    queryset = Route.objects.all().select_related(
        "source", "destination"
    )
    serializer_class = RouteSerializer

    def get_queryset(self):
        source_id_str = self.request.query_params.get("source")
        destination_id_str = self.request.query_params.get(
            "destination"
        )

        queryset = self.queryset

        if source_id_str:
            queryset = queryset.filter(source_id=int(source_id_str))

        if destination_id_str:
            queryset = queryset.filter(
                destination_id=int(destination_id_str)
            )

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return RouteListSerializer

        if self.action == "retrieve":
            return RouteDetailSerializer

        return RouteSerializer


class TrainTypeViewSet(viewsets.ModelViewSet):
    queryset = TrainType.objects.all()
    serializer_class = TrainTypeSerializer


class TrainViewSet(viewsets.ModelViewSet):
    queryset = Train.objects.all().select_related("train_type")
    serializer_class = TrainSerializer

    def get_queryset(self):
        name = self.request.query_params.get("name")
        train_type_id_str = self.request.query_params.get(
            "train_type"
        )

        queryset = self.queryset

        if name:
            queryset = queryset.filter(name__icontains=name)

        if train_type_id_str:
            queryset = queryset.filter(
                train_type_id=int(train_type_id_str)
            )

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return TrainListSerializer

        return TrainSerializer


class CrewViewSet(viewsets.ModelViewSet):
    queryset = Crew.objects.all()
    serializer_class = CrewSerializer


class JourneyViewSet(viewsets.ModelViewSet):
    queryset = (
        Journey.objects.all()
        .select_related(
            "route",
            "route__source",
            "route__destination",
            "train",
            "train__train_type"
        )
        .prefetch_related("crews")
        .annotate(
            tickets_available=(
                F("train__cargo_num") * F("train__place_in_cargo")
                - Count("tickets")
            )
        )
    )
    serializer_class = JourneySerializer

    def get_queryset(self):
        departure_date = self.request.query_params.get(
            "departure_date"
        )

        queryset = self.queryset

        if departure_date:
            date = datetime.strptime(
                departure_date, "%Y-%m-%d"
            ).date()
            queryset = queryset.filter(departure_date=date)

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return JourneyListSerializer

        if self.action == "retrieve":
            return JourneyDetailSerializer

        return JourneySerializer


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return OrderListSerializer

        return OrderSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
