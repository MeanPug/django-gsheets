from googleapiclient.discovery import build
from django.core.exceptions import ObjectDoesNotExist
from .auth import get_gapi_credentials
from .gsheets import SheetPullInterface, SheetPushInterface, SheetSync
import string
import re
import logging

logger = logging.getLogger(__name__)


class BaseGoogleSheetMixin(object):
    """ base mixin for google sheets """
    # ID of a Google Sheets spreadsheet
    spreadsheet_id = None
    # name of the sheet inside the spreadsheet to use
    sheet_name = 'Sheet1'
    # range of data in the sheet
    data_range = 'A1:Z'
    # name of the field to use as the ID field for model instances in the sync'd sheet
    model_id_field = 'id'
    # name of the sheet column to use to store the ID of the Django model instance
    sheet_id_field = 'Django GUID'
    # the batch size determines at what point sheet data is written-out to the Google sheet
    batch_size = 500
    # the max rows to support in the sheet
    max_rows = 30000
    # max column to support in the sheet
    max_col = 'Z'


class SheetPushableMixin(BaseGoogleSheetMixin):
    """ mixes in functionality to push data from a Django model to a google sheet. """
    @classmethod
    def push_to_sheet(cls):
        interface = SheetPushInterface(cls, cls.spreadsheet_id, sheet_name=cls.sheet_name, data_range=cls.data_range,
                                       model_id_field=cls.model_id_field, sheet_id_field=cls.sheet_id_field,
                                       batch_size=cls.batch_size, max_rows=cls.max_rows, max_col=cls.max_col,
                                       push_fields=cls.get_sheet_push_fields(), queryset=cls.get_sheet_queryset())
        return interface.upsert_table()

    @classmethod
    def get_sheet_queryset(cls):
        return cls.objects.all()

    @classmethod
    def get_sheet_push_fields(cls):
        return [f.name for f in cls._meta.fields]


class SheetPullableMixin(BaseGoogleSheetMixin):
    """ mixes in functionality to pull data from a google sheet and use that data to keep model data updated. Notes:
    * won't delete rows that are in the DB but not in the sheet
    * won't delete rows that are in the sheet but not the DB
    * will update existing row values with values from the sheet
    """
    @classmethod
    def pull_sheet(cls):
        interface = SheetPullInterface(cls, cls.spreadsheet_id, sheet_name=cls.sheet_name, data_range=cls.data_range,
                                       model_id_field=cls.model_id_field, sheet_id_field=cls.sheet_id_field,
                                       batch_size=cls.batch_size, max_rows=cls.max_rows, max_col=cls.max_col, pull_fields=cls.get_sheet_pull_fields())

        return interface.pull_sheet()

    @classmethod
    def get_sheet_pull_fields(cls):
        """ get the field names from the sheet which are to be pulled. MUST INCLUDE THE sheet_id_field """
        return 'all'


class SheetSyncableMixin(SheetPushableMixin, SheetPullableMixin):
    """ mixes in ability to 2-way sync data from/to a google sheet """
    @classmethod
    def sync_sheet(cls):
        cls.pull_sheet()
        cls.push_to_sheet()
