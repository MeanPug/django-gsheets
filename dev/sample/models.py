from django.db import models
from gsheets import mixins
from uuid import uuid4


class Person(mixins.SheetPushableMixin, models.Model):
    spreadsheet_id = '18F_HLftNtaouHgA3fmfT2M1Va9oO-YWTBw2EDsuz8V4'
    model_id_field = 'guid'

    guid = models.CharField(primary_key=True, max_length=255, default=uuid4)

    first_name = models.CharField(max_length=127)
    last_name = models.CharField(max_length=127)
    email = models.CharField(max_length=127, null=True, blank=True, default=None)
    phone = models.CharField(max_length=127, null=True, blank=True, default=None)

    def __str__(self):
        return f'{self.first_name} {self.last_name} // {self.email} ({self.guid})'
