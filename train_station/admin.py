from django.contrib import admin

from train_station.models import Station, Route, TrainType, Train, Journey, Ticket, Order

admin.site.register(Station)
admin.site.register(Route)
admin.site.register(TrainType)
admin.site.register(Train)
admin.site.register(Journey)
admin.site.register(Order)
admin.site.register(Ticket)
