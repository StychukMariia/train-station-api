from django.core.management.base import BaseCommand
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
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "Seed the database with sample data matching current models"

    def handle(self, *args, **kwargs):
        self.stdout.write("Cleaning up old data...")
        Ticket.objects.all().delete()
        Order.objects.all().delete()
        Journey.objects.all().delete()
        Route.objects.all().delete()
        Train.objects.all().delete()
        TrainType.objects.all().delete()
        Crew.objects.all().delete()
        Station.objects.all().delete()

        self.stdout.write("Creating stations...")
        station1 = Station.objects.create(
            name="Kyiv-Pasazhyrskyi", latitude=50.4402, longitude=30.4884
        )
        station2 = Station.objects.create(
            name="Lviv", latitude=49.8397, longitude=24.0297
        )
        station3 = Station.objects.create(
            name="Odesa-Holovna", latitude=46.4694, longitude=30.7403
        )
        station4 = Station.objects.create(
            name="Kharkiv-Pasazhyrskyi", latitude=49.9935, longitude=36.2304
        )

        self.stdout.write("Creating routes...")
        route1 = Route.objects.create(
            source=station1, destination=station2, distance=540
        )
        route2 = Route.objects.create(
            source=station1, destination=station3, distance=475
        )
        route3 = Route.objects.create(
            source=station1, destination=station4, distance=480
        )

        self.stdout.write("Creating train types...")
        tt_express = TrainType.objects.create(name="Intercity Express")
        tt_night = TrainType.objects.create(name="Night Train")

        self.stdout.write("Creating trains...")
        train1 = Train.objects.create(
            name="Kyiv-Lviv #743",
            cargo_num=10,
            places_in_cargo=50,
            train_type=tt_express,
        )
        train2 = Train.objects.create(
            name="Kyiv-Odesa #105",
            cargo_num=14,
            places_in_cargo=36,
            train_type=tt_night,
        )
        train3 = Train.objects.create(
            name="Kyiv-Kharkiv #722",
            cargo_num=8,
            places_in_cargo=48,
            train_type=tt_express,
        )

        self.stdout.write("Creating crew members...")
        crew1 = Crew.objects.create(first_name="Andrii", last_name="Shevchenko")
        crew2 = Crew.objects.create(first_name="Olena", last_name="Koval")
        crew3 = Crew.objects.create(first_name="Dmytro", last_name="Melnyk")

        self.stdout.write("Creating journeys...")
        journey1 = Journey.objects.create(
            route=route1,
            train=train1,
            departure_time="2026-10-15T08:00:00Z",
            arrival_time="2026-10-15T13:30:00Z",
        )
        journey1.crews.add(crew1, crew2)

        journey2 = Journey.objects.create(
            route=route2,
            train=train2,
            departure_time="2026-10-16T22:00:00Z",
            arrival_time="2026-10-17T06:00:00Z",
        )
        journey2.crews.add(crew2, crew3)

        journey3 = Journey.objects.create(
            route=route3,
            train=train3,
            departure_time="2026-10-18T07:15:00Z",
            arrival_time="2026-10-18T11:50:00Z",
        )
        journey3.crews.add(crew1, crew3)

        self.stdout.write("Creating test users and orders...")
        user1, _ = User.objects.get_or_create(email="user1@train.com")
        if not user1.has_usable_password():
            user1.set_password("testpassword123")
            user1.save()

        user2, _ = User.objects.get_or_create(email="user2@train.com")
        if not user2.has_usable_password():
            user2.set_password("testpassword123")
            user2.save()

        order1 = Order.objects.create(user=user1)
        Ticket.objects.create(cargo=1, seat=12, journey=journey1, order=order1)
        Ticket.objects.create(cargo=1, seat=13, journey=journey1, order=order1)

        order2 = Order.objects.create(user=user2)
        Ticket.objects.create(cargo=2, seat=5, journey=journey2, order=order2)
        Ticket.objects.create(cargo=2, seat=6, journey=journey2, order=order2)

        self.stdout.write(
            self.style.SUCCESS(
                "Database successfully seeded with models-compliant data!"
            )
        )
