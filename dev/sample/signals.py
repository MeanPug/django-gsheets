from django.dispatch import receiver
from django.core.exceptions import ObjectDoesNotExist
from gsheets.signals import sheet_row_processed
from .models import Car, Person


@receiver(sheet_row_processed, sender=Car)
def tie_car_to_owner(instance=None, created=None, row_data=None, **kwargs):
    try:
        instance.owner = Person.objects.get(last_name__iexact=row_data['owner_last_name'])
        instance.save()
    except (ObjectDoesNotExist, KeyError):
        pass
