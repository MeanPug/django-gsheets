from django.contrib import admin
from .models import Person


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    fields = ('first_name', 'last_name', 'email', 'phone',)
