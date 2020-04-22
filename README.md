# django-gsheets
Django app for keeping models and google sheets synced

## Purpose
django-gsheets is a pluggable Django app that adds functionality (via mixins) to models allowing them to sync data to and from Google Sheets. The app errs on the side of caution in that deletions from your DB won't propagate to the sheet and visa versa.

## Installation
### Install django-gsheets
```
pip install django-gsheets
```
### Add django-gsheets to INSTALLED_APPS
```python
INSTALLED_APPS = [
    ...
    'gsheets',
    ...
]
```
After adding, make sure to run `migrate`

### Create a Google Cloud Project and Download OAuth Client Secrets
Google has a good guide for that [here](https://developers.google.com/sheets/api/quickstart/python) (you only need to do Step 1).

### Update Project Settings
Update your project settings to tell django-gsheets where the downloaded credentials are. You should just need the following:
```python
GSHEETS = {
    'CLIENT_SECRETS': '<PATH TO DOWNLOADED CREDS>'
}
```

## Usage
In order to provide two-way sync capability to a models' data, all you need to do is add the `SheetSyncableMixin` to it and tell the model what sheet to use. For example:

```python
from django.db import models
from gsheets import mixins
from uuid import uuid4


class Person(mixins.SheetSyncableMixin, models.Model):
    spreadsheet_id = '18F_HLftNtaouHgA3fmfT2M1Va9oO-YWTBw2EDsuz8V4'
    model_id_field = 'guid'

    guid = models.CharField(primary_key=True, max_length=255, default=uuid4)

    first_name = models.CharField(max_length=127)
    last_name = models.CharField(max_length=127)
    email = models.CharField(max_length=127, null=True, blank=True, default=None)
    phone = models.CharField(max_length=127, null=True, blank=True, default=None)

    def __str__(self):
        return f'{self.first_name} {self.last_name} // {self.email} ({self.guid})'
```
To two-way sync sheet data, simply run `Person.sync_sheet()`.

If you want to be more fine-grained and have models that either just push to Google Sheets or just pull, you can swap `SheetSyncableMixin` for `SheetPushableMixin` or `SheetPullableMixin` (respectively).

### Further Configuration
You can further configure the functionality of sheet sync by specifying any of the following fields on the model.

| Field  | Default | Description |
| ------------- | ------------- | ------------- |
| spreadsheet_id  | None  | designates the Google Sheet to sync  |
| sheet_name  | Sheet1  | the name of the sheet in the Google Sheet  |
| data_range  | A1:Z  | the range of data in the sheet to keep synced. First row must contain field names that match model fields.  |
| model_id_field  | id  | the name of the model field storing a unique ID for each row  |
| sheet_id_field  | Django GUID  | the name of the field in the synced sheet that will store model instance IDs  |
| batch_size  | 500  | (internal) the batch size to use when updating sheets with progress  |
| max_rows  | 30000  | (internal) used for internal calculations, don't change unless you know what you're doing  |
| max_col  | Z  | (internal) used for internal calculations, don't change unless you know what you're doing  |

## Management Commands
If you don't want to manually sync data to and from models to gsheets, `django-gsheets` ships with a handy management command that automatically discovers all models mixing in one of `SheetPullableMixin`, `SheetPushableMixin`, or `SheetSyncableMixin` and runs the appropriate sync command. To execute, simply run `python manage.py syncgsheets`.
