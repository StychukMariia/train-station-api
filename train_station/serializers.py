from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from train_station.models import (
    Station,
    Route,
    TrainType,
    Train,
    Crew,
    Journey,
    Order,
    Ticket,
)


class StationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Station
        fields = ("id", "name", "latitude", "longitude")


class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = ("id", "source", "destination", "distance")


class RouteListSerializer(RouteSerializer):
    source = serializers.SlugRelatedField(
        many=False, read_only=True, slug_field="name"
    )
    destination = serializers.SlugRelatedField(
        many=False, read_only=True, slug_field="name"
    )


class RouteDetailSerializer(RouteSerializer):
    source = StationSerializer(many=False, read_only=True)
    destination = StationSerializer(many=False, read_only=True)


class TrainTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainType
        fields = ("id", "name")


class TrainSerializer(serializers.ModelSerializer):
    train_type = TrainTypeSerializer(many=False, read_only=True)

    class Meta:
        model = Train
        fields = (
            "id",
            "name",
            "cargo_num",
            "place_in_cargo",
            "capacity",
            "train_type"
        )


class TrainListSerializer(TrainSerializer):
    train_type = serializers.SlugRelatedField(
        many=False, read_only=True, slug_field="name"
    )


class CrewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Crew
        fields = ("id", "first_name", "last_name", "full_name")


class JourneySerializer(serializers.ModelSerializer):
    class Meta:
        model = Journey
        fields = (
            "id",
            "route",
            "train",
            "departure_date",
            "arrival_date",
            "crews"
        )


class JourneyListSerializer(JourneySerializer):
    route_source = serializers.CharField(
        source="route.source.name",
        read_only=True
    )
    route_destination = serializers.CharField(
        source="route.destination.name",
        read_only=True
    )
    train_name = serializers.CharField(
        source="train.name",
        read_only=True
    )
    train_capacity = serializers.IntegerField(
        source="train.capacity",
        read_only=True
    )
    tickets_available = serializers.IntegerField()
    crews = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="full_name"
    )

    class Meta:
        model = Journey
        fields = (
            "id",
            "route_source",
            "route_destination",
            "train_name",
            "train_capacity",
            "tickets_available",
            "departure_date",
            "arrival_date",
            "crews"
        )


class TicketSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        data = super(TicketSerializer, self).validate(attrs=attrs)
        Ticket.validate_ticket(
            attrs["cargo"],
            attrs["seat"],
            attrs["journey"].train,
            ValidationError
        )
        return data

    class Meta:
        model = Ticket
        fields = ("id", "cargo", "seat", "journey")


class TicketListSerializer(TicketSerializer):
    journey = JourneyListSerializer(many=False, read_only=True)


class TicketSeatsSerializer(TicketSerializer):
    class Meta:
        model = Ticket
        fields = ("cargo", "seat")


class JourneyDetailSerializer(JourneySerializer):
    route = RouteListSerializer(many=False, read_only=True)
    train = TrainListSerializer(many=False, read_only=True)
    crews = CrewSerializer(many=True, read_only=True)
    taken_place = TicketSeatsSerializer(
        source="tickets", many=True, read_only=True
    )

    class Meta:
        model = Journey
        fields = (
            "id",
            "route",
            "train",
            "departure_date",
            "arrival_date",
            "crews",
            "taken_place",
        )


class OrderSerializer(serializers.ModelSerializer):
    tickets = TicketSerializer(
        many=True, read_only=False, allow_empty=False
    )

    class Meta:
        model = Order
        fields = ("id", "created_at", "user", "tickets")

    def create(self, validated_data):
        with transaction.atomic():
            tickets_data = validated_data.pop("tickets")
            order = Order.objects.create(**validated_data)
            for ticket_data in tickets_data:
                Ticket.objects.create(order=order, **ticket_data)
            return order


class OrderListSerializer(OrderSerializer):
    tickets = TicketListSerializer(many=True, read_only=True)
