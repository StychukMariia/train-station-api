from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q, F

from core import settings


class Station(models.Model):
    name = models.CharField(max_length=100, unique=True)
    latitude = models.FloatField(
        validators=[MinValueValidator(-90.0), MaxValueValidator(90.0)]
    )
    longitude = models.FloatField(
        validators=[MinValueValidator(-180.0), MaxValueValidator(180.0)]
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(latitude__gte=-90.0) & Q(latitude__lte=90.0),
                name="latitude_valid_range",
            ),
            models.CheckConstraint(
                condition=Q(longitude__gte=-180.0) & Q(longitude__lte=180.0),
                name="longitude_valid_range",
            ),
        ]

    def __str__(self):
        return self.name


class Route(models.Model):
    source = models.ForeignKey(
        Station,
        on_delete=models.CASCADE,
        related_name="routes_from",
    )
    destination = models.ForeignKey(
        Station, on_delete=models.CASCADE, related_name="routes_to"
    )
    distance = models.IntegerField(validators=[MinValueValidator(1)])

    class Meta:
        unique_together = ("source", "destination")
        constraints = [
            models.CheckConstraint(
                condition=Q(distance__gt=0),
                name="route_distance_positive",
            ),
            models.CheckConstraint(
                condition=~Q(source=F("destination")),
                name="source_destination_different",
            ),
        ]

    def clean(self):
        super().clean()
        if self.source == self.destination:
            raise DjangoValidationError(
                {"destination": "Source and destination stations must be different."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.source.name} - {self.destination.name}"


class TrainType(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Train(models.Model):
    name = models.CharField(max_length=100, unique=True)
    cargo_num = models.IntegerField(validators=[MinValueValidator(1)])
    places_in_cargo = models.IntegerField(validators=[MinValueValidator(1)])
    train_type = models.ForeignKey(
        TrainType,
        on_delete=models.CASCADE,
        related_name="trains",
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(cargo_num__gt=0),
                name="train_cargo_num_positive",
            ),
            models.CheckConstraint(
                condition=Q(places_in_cargo__gt=0),
                name="train_places_in_cargo_positive",
            ),
        ]

    @property
    def capacity(self) -> int:
        return self.cargo_num * self.places_in_cargo

    def __str__(self):
        return self.name


class Crew(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return self.first_name + " " + self.last_name


class Journey(models.Model):
    route = models.ForeignKey(
        Route,
        on_delete=models.CASCADE,
        related_name="journeys",
    )
    train = models.ForeignKey(Train, on_delete=models.CASCADE, related_name="journeys")
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()
    crews = models.ManyToManyField(Crew, blank=True, related_name="journeys")

    class Meta:
        ordering = ["-departure_time"]

    def clean(self):
        super().clean()
        if self.departure_time and self.arrival_time:
            if self.arrival_time <= self.departure_time:
                raise DjangoValidationError(
                    {"arrival_time": "Arrival time must be later than departure time."}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.train.name} ({self.departure_time} - {self.arrival_time})"


class Order(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return str(self.created_at)


class Ticket(models.Model):
    cargo = models.IntegerField(validators=[MinValueValidator(1)])
    seat = models.IntegerField(validators=[MinValueValidator(1)])
    journey = models.ForeignKey(
        Journey, on_delete=models.CASCADE, related_name="tickets"
    )
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="tickets")

    @staticmethod
    def validate_ticket(cargo, seat, journey, error_to_raise, current_ticket_id=None):
        train = journey.train
        for ticket_attr_value, ticket_attr_name, train_attr_name in [
            (cargo, "cargo", "cargo_num"),
            (seat, "seat", "places_in_cargo"),
        ]:
            count_attrs = getattr(train, train_attr_name)
            if not (1 <= ticket_attr_value <= count_attrs):
                raise error_to_raise(
                    {
                        ticket_attr_name: f"{ticket_attr_name} "
                        f"number must be in available range: "
                        f"(1, {train_attr_name}): "
                        f"(1, {count_attrs})"
                    }
                )

        existing_tickets = Ticket.objects.filter(
            journey=journey, cargo=cargo, seat=seat
        )
        if current_ticket_id:
            existing_tickets = existing_tickets.exclude(id=current_ticket_id)

        if existing_tickets.exists():
            raise error_to_raise(
                {
                    "non_field_errors": f"This seat (cargo: {cargo}, seat: {seat}) is already booked for this journey."
                }
            )

    def clean(self):
        Ticket.validate_ticket(
            self.cargo,
            self.seat,
            self.journey,
            DjangoValidationError,
        )

    def save(
        self,
        *args,
        **kwargs,
    ):
        self.full_clean()
        return super(Ticket, self).save(*args, **kwargs)

    class Meta:
        unique_together = ("journey", "cargo", "seat")
        ordering = ["cargo", "seat"]
        constraints = [
            models.CheckConstraint(
                condition=Q(cargo__gt=0),
                name="ticket_cargo_positive",
            ),
            models.CheckConstraint(
                condition=Q(seat__gt=0),
                name="ticket_seat_positive",
            ),
        ]

    def __str__(self):
        return f"{str(self.journey)} (row: {self.cargo}, seat: {self.seat})"
