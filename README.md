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
To use

## Management Commands
If you don't want to manually sync data to and from models to gsheets, `django-gsheets` ships with a handy management command that automatically discovers all models mixing in one of `SheetPullableMixin`, `SheetPushableMixin`, or `SheetSyncableMixin` and runs the appropriate sync command. To execute, simply run `python manage.py syncgsheets`.
