from django.contrib import admin
from .models import Person, Car


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    fields = ('first_name', 'last_name', 'email', 'phone',)


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    fields = ('owner', 'brand', 'color',)
