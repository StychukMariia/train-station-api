from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.core.exceptions import ValidationError as DjangoValidationError

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

    def validate(self, attrs):
        data = super().validate(attrs)
        source = data.get("source")
        destination = data.get("destination")
        distance = data.get("distance")

        if source and destination and source == destination:
            raise serializers.ValidationError(
                {"destination": "Source and destination stations must be different."}
            )
        if distance is not None and distance <= 0:
            raise serializers.ValidationError(
                {"distance": "Distance must be a positive integer."}
            )
        return data


class RouteListSerializer(RouteSerializer):
    source = serializers.SlugRelatedField(many=False, read_only=True, slug_field="name")
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
    train_type_id = serializers.PrimaryKeyRelatedField(
        queryset=TrainType.objects.all(), source="train_type", write_only=True
    )

    class Meta:
        model = Train
        fields = (
            "id",
            "name",
            "cargo_num",
            "places_in_cargo",
            "capacity",
            "train_type",
            "train_type_id",
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
        fields = ("id", "route", "train", "departure_time", "arrival_time", "crews")

    def validate(self, attrs):
        data = super().validate(attrs)
        departure_time = data.get("departure_time")
        arrival_time = data.get("arrival_time")

        if departure_time and arrival_time and arrival_time <= departure_time:
            raise serializers.ValidationError(
                {"arrival_time": "Arrival time must be later than departure time."}
            )
        return data


class JourneyListSerializer(JourneySerializer):
    route_source = serializers.CharField(source="route.source.name", read_only=True)
    route_destination = serializers.CharField(
        source="route.destination.name", read_only=True
    )
    train_name = serializers.CharField(source="train.name", read_only=True)
    train_capacity = serializers.IntegerField(source="train.capacity", read_only=True)
    tickets_available = serializers.SerializerMethodField()
    crews = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="full_name"
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
            "departure_time",
            "arrival_time",
            "crews",
        )

    def get_tickets_available(self, obj):
        if hasattr(obj, "tickets_available"):
            return obj.tickets_available

        booked_tickets = obj.tickets.count()
        total_places = obj.train.cargo_num * obj.train.places_in_cargo
        return total_places - booked_tickets


class TicketSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        data = super(TicketSerializer, self).validate(attrs=attrs)
        try:
            Ticket.validate_ticket(
                attrs["cargo"], attrs["seat"], attrs["journey"], DRFValidationError
            )
        except DjangoValidationError as e:
            raise DRFValidationError(
                e.message_dict if hasattr(e, "message_dict") else str(e)
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
    taken_place = TicketSeatsSerializer(source="tickets", many=True, read_only=True)

    class Meta:
        model = Journey
        fields = (
            "id",
            "route",
            "train",
            "departure_time",
            "arrival_time",
            "crews",
            "taken_place",
        )


class OrderSerializer(serializers.ModelSerializer):
    tickets = TicketSerializer(many=True, read_only=False, allow_empty=False)

    class Meta:
        model = Order
        fields = ("id", "created_at", "tickets")

    def create(self, validated_data):
        tickets_data = validated_data.pop("tickets")

        with transaction.atomic():
            journey_ids = [ticket_data["journey"].id for ticket_data in tickets_data]
            journeys = list(
                Journey.objects.filter(id__in=journey_ids).select_for_update()
            )
            journey_map = {j.id: j for j in journeys}

            for journey_id in set(journey_ids):
                journey = journey_map.get(journey_id)
                if not journey:
                    raise DRFValidationError(
                        {"journey": f"Journey with id {journey_id} does not exist."}
                    )

                total_capacity = journey.train.cargo_num * journey.train.places_in_cargo
                booked_tickets_count = journey.tickets.count()
                requested_tickets_count = sum(
                    1 for t in tickets_data if t["journey"].id == journey_id
                )

                if booked_tickets_count + requested_tickets_count > total_capacity:
                    raise DRFValidationError(
                        {
                            "non_field_errors": f"Journey (id={journey.id}) is fully booked or does not have enough available seats."
                        }
                    )

            order = Order.objects.create(**validated_data)
            for ticket_data in tickets_data:
                Ticket.objects.create(order=order, **ticket_data)

        return order


class OrderListSerializer(OrderSerializer):
    tickets = TicketListSerializer(many=True, read_only=True)
