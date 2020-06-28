from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from django.core.exceptions import ObjectDoesNotExist
from .auth import get_gapi_credentials
from .signals import sheet_row_processed
from . import decorators
import string
import re
import logging

logger = logging.getLogger(__name__)


class BaseSheetInterface(object):
    def __init__(self, model_cls, spreadsheet_id, sheet_name=None, data_range=None, model_id_field=None,
                 sheet_id_field=None, batch_size=None, max_rows=None, max_col=None, **kwargs):
        """
        :param model_cls: `models.Model` subclass this interface applies to
        :param spreadsheet_id: `str` ID of a Google Sheets spreadsheet
        :param sheet_name: `str` name of the sheet inside the spreadsheet to use
        :param data_range: `str` range of data in the sheet
        :param model_id_field: `str` name of the field to use as the ID field for model instances in the sync'd sheet
        :param sheet_id_field: `str` name of the sheet column to use to store the ID of the Django model instance
        :param batch_size: `int` the batch size determines at what point sheet data is written-out to the Google sheet
        :param max_rows: `int` the max rows to support in the sheet
        :param max_col: `str` max column to support in the sheet
        """
        self.model_cls = model_cls
        self.spreadsheet_id = spreadsheet_id
        self.sheet_name = sheet_name
        self.data_range = data_range
        self.model_id_field = model_id_field
        self.sheet_id_field = sheet_id_field
        self.batch_size = batch_size
        self.max_rows = max_rows
        self.max_col = max_col

        self._api = None
        self._credentials = None
        self._sheet_data = None
        self._sheet_headers = None

    @property
    def credentials(self):
        """ gets an Credentials instance to use for request auth
        :return `google.oauth2.Credentials`
        :raises: `ValueError` if no credentials have been created
        """
        from .models import AccessCredentials

        if self._credentials:
            return self._credentials

        ac = AccessCredentials.objects.order_by('-created_time').first()
        if ac is None:
            raise ValueError('you must authenticate gsheets at /gsheets/authorize/ before usage')

        self._credentials = get_gapi_credentials(ac)

        return self._credentials

    @property
    def api(self):
        if self._api is not None:
            return self._api

        self._api = build('sheets', 'v4', credentials=self.credentials)
        return self._api

    @property
    def sheet_data(self):
        if self._sheet_data is not None:
            return self._sheet_data

        api_res = self.api.spreadsheets().values().get(spreadsheetId=self.spreadsheet_id, range=self.sheet_range).execute()
        self._sheet_data = api_res.get('values', [])
        self._sheet_headers = self._sheet_data[0]
        # remove the headers from the data
        self._sheet_data = self._sheet_data[1:]

        return self._sheet_data

    @property
    def sheet_headers(self):
        if not self._sheet_headers:
            # self.sheet_data sets the headers
            noop = self.sheet_data

        return self._sheet_headers

    @property
    def sheet_range(self):
        return BaseSheetInterface.get_sheet_range(self.sheet_name, self.data_range)

    @property
    def sheet_range_rows(self):
        """
        :return: `two-tuple`
        """
        row_match = re.search('[A-Z]+(\d+):[A-Z]+(\d*)', self.sheet_range)
        try:
            start, end = row_match.groups()
        except ValueError:
            start, end = row_match.groups()[0], self.max_rows

        if end == '':
            end = self.max_rows

        return int(start), int(end)

    @property
    def sheet_range_cols(self):
        """
        :return: `two-tuple`
        """
        col_match = re.search('([A-Z]+)\d*:([A-Z]+)\d*', self.sheet_range)
        try:
            start, end = col_match.groups()
        except ValueError:
            start, end = col_match.groups()[0], self.max_col

        return start, end

    @staticmethod
    def convert_col_letter_to_number(col_letter):
        """ converts a column letter - like 'A' - to it's index in the alphabet """
        return string.ascii_lowercase.index(col_letter.lower())

    @staticmethod
    def convert_col_number_to_letter(col_number):
        """ converts a column index - like 1 - to it's alphabetic equivalent (like 'A') """
        return string.ascii_lowercase[col_number].upper()

    @staticmethod
    def get_sheet_range(sheet_name, data_range):
        return '!'.join([sheet_name, data_range])

    def column_index(self, field_name):
        """ given a canonical field name (like 'Name'), get the column index of that field in the sheet. This relies
        on the first row in the sheet having a cell with the name of the given field
        :param field_name: `str`
        :return: `int` index of the column in the sheet storing the given fields' data
        :raises: `ValueError` if the field name doesn't exist in the header row
        """
        logger.debug(f'got header row {self.sheet_headers}')

        return self.sheet_headers.index(field_name)

    def existing_row(self, **data):
        """ given the data to be synced to a row, check if it already exists in the sheet and - if it does - return
        its index
        :param data: `dict` of fields/values
        :return: `int` the index of the row containing the ID if it exists, None otherwise
        :raises: `KeyError` if the data doesn't contain the ID field for the model
        :raises: `ValueError` if the columns don't contain the Sheet ID col
        """
        model_id = data[self.model_id_field]
        sheet_id_ix = self.column_index(self.sheet_id_field)

        # look through the sheet ID column for the model ID
        for i, r in enumerate(self.sheet_data):
            try:
                if r[sheet_id_ix] == str(model_id):
                    return i
            except IndexError:
                continue

        return None

    @decorators.backoff_on_exception(decorators.expo, HttpError)
    def writeout(self, range, data):
        """ writes the given data to the given range in the spreadsheet (without batching)
        :param range: `str` a range (like 'Sheet1!A2:B3') to write data to
        :param data: `list` of `list` the set of data to write
        """
        body = {
            'values': data
        }

        return self.api.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id, range=range, valueInputOption='USER_ENTERED', body=body
        ).execute()

    @decorators.backoff_on_exception(decorators.expo, HttpError)
    def writeout_batch(self, ranges, data):
        """ writes the given data to the given ranges in the spreadsheet
        :param ranges: `list` of `str` ranges (like 'Sheet1!A2:B3') to write data to
        :param data: `list` of `list` of `list` the set of data to write to the list of ranges
        :raises: `ValueError` if the list of ranges and data don't have the same length
        """
        if len(ranges) != len(data):
            raise ValueError(f'the length of ranges ({len(ranges)} must equal the length of data ({len(data)})')

        request_data = zip(ranges, data)
        request_body = {
            'value_input_option': 'USER_ENTERED',
            'data': [{'range': r, 'values': values} for r, values in request_data]
        }

        request = self.api.spreadsheets().values().batchUpdate(spreadsheetId=self.spreadsheet_id, body=request_body)
        response = request.execute()

        logger.debug(f'got response {response} executing writeout in range {range}')

        return response


class SheetPushInterface(BaseSheetInterface):
    """ functionality to push data from a Django model to a google sheet. """
    def __init__(self, *args, **kwargs):
        super(SheetPushInterface, self).__init__(*args, **kwargs)
        self.queryset = kwargs.pop('queryset')
        self.push_fields = kwargs.pop('push_fields', [f.name for f in self.model_cls._meta.fields])

    def upsert_table(self):
        """ upserts objects of this instance type to Sheets """
        queryset = self.queryset
        last_writeout = 0
        cols_start, cols_end = self.sheet_range_cols
        rows_start, rows_end = self.sheet_range_rows

        for i, obj in enumerate(queryset):
            if i > 0 and i % self.batch_size == 0:
                writeout_range_start_row = (rows_start + 1) + i
                writeout_range_end_row = writeout_range_start_row + self.batch_size
                writeout_range = BaseSheetInterface.get_sheet_range(
                    self.sheet_name, f'{cols_start}{writeout_range_start_row}:{cols_end}{writeout_range_end_row}'
                )

                writeout_data_start_row = (rows_start - 1) + i
                writeout_data_end_row = writeout_data_start_row + self.batch_size
                writeout_data = self.sheet_data[writeout_data_start_row:writeout_data_end_row]

                logger.debug(f'writing out {len(writeout_data)} rows of data to {writeout_range}')

                self.writeout_batch([writeout_range], [writeout_data])
                last_writeout = i

            push_data = {f: getattr(obj, f) for f in self.push_fields}
            self.upsert_sheet_data(**push_data)

        # writeout any remaining data
        if last_writeout < len(queryset):
            logger.debug(f'writing out {len(queryset) - last_writeout} final rows of data')
            writeout_range = BaseSheetInterface.get_sheet_range(
                self.sheet_name, f'{cols_start}{max(2, last_writeout)}:{cols_end}{rows_end}'
            )
            self.writeout_batch([writeout_range], [self.sheet_data[last_writeout:]])

        logger.info('FINISHED WITH TABLE UPSERT')

    def upsert_sheet_data(self, **data):
        """ upserts the data, given as a dict of field/values, to the sheet. If the data already exists, replaces
        its previous value
        :param data: `dict` of field/value
        """
        field_indexes = []
        for field in data.keys():
            try:
                field_indexes.append((field, self.column_index(field if field != self.model_id_field else self.sheet_id_field)))
            except ValueError:
                logger.info(f'skipping field {field} because it has no header')

        # order the field indexes by their col index
        sorted_field_indexes = sorted(field_indexes, key=lambda x: x[1])

        row_data = []
        for field, ix in sorted_field_indexes:
            logger.debug(f'writing data in field {field} to col ix {ix}')
            row_data.append(data[field])

        # get the row to update if it exists, otherwise we will add a new row
        existing_row_ix = self.existing_row(**data)
        if existing_row_ix is not None:
            self.sheet_data[existing_row_ix] = row_data
        else:
            self.sheet_data.append(row_data)


class SheetPullInterface(BaseSheetInterface):
    """ functionality to pull data from a google sheet and use that data to keep model data updated. Notes:
    * won't delete rows that are in the DB but not in the sheet
    * won't delete rows that are in the sheet but not the DB
    * will update existing row values with values from the sheet
    """
    def __init__(self, *args, **kwargs):
        super(SheetPullInterface, self).__init__(*args, **kwargs)
        self.pull_fields = kwargs.pop('pull_fields', 'all')

    def pull_sheet(self):
        sheet_fields = self.pull_fields
        rows_start, rows_end = self.sheet_range_rows
        field_indexes = {self.column_index(f): f for f in self.sheet_headers if f in sheet_fields or sheet_fields == 'all'}
        instances = []
        writeout_batch = []

        for row_ix, row in enumerate(self.sheet_data):
            if len(writeout_batch) >= self.batch_size:
                logger.debug('writing out a batch of instance IDs')
                self.writeout_created_instance_ids(writeout_batch)
                writeout_batch = []

            row_data = {}

            for col_ix in range(len(row)):
                if col_ix in field_indexes:
                    field = field_indexes[col_ix]
                    value = row[col_ix]

                    row_data[field] = value

            cleaned_row_data = getattr(self.model_cls, 'clean_row_data')(row_data) if hasattr(self.model_cls, 'clean_row_data') else row_data

            # give the model the ability to prevent a row from running through upsert
            if hasattr(self.model_cls, 'should_upsert_row') and not getattr(self.model_cls, 'should_upsert_row')(cleaned_row_data):
                logger.debug(f'model prevented upsert of row {row_ix}')
                continue

            instance, created = self.upsert_model_data(row_ix, **cleaned_row_data)

            instances.append(instance)
            if created:
                writeout_batch.append((instance, rows_start + row_ix + 1)) # + 1 to not count header

        if len(writeout_batch) > 0:
            logger.debug(f'writing out remaining {len(writeout_batch)} instance IDs')
            self.writeout_created_instance_ids(writeout_batch)

        return instances

    def upsert_model_data(self, row_ix, **data):
        """ takes a dict of field/value information from the sheet and inserts or updates a model instance
        with that data
        :param row_ix: `int` index of the row which is being upserted into a model instance
        :param data: `dict`
        """
        model_fields = {f.name for f in self.model_cls._meta.get_fields()}
        # cleaned data
        cleaned_data = {
            field: getattr(self.model_cls, f'clean_{field}_data')(value) if hasattr(self.model_cls, f'clean_{field}_data') else value
            for field, value in data.items() if field != self.sheet_id_field and field in model_fields
        }

        try:
            row_id = data[self.sheet_id_field]

            model_filter = {
                self.model_id_field: row_id
            }
            instance, created = self.model_cls.objects.get(**model_filter), False
        except (KeyError, ObjectDoesNotExist, ValueError):
            logger.debug(f'creating new model instance')
            # if there's no ID field in the row or the ID doesnt exist
            instance, created = self.model_cls.objects.create(**cleaned_data), True

        if not created:
            logger.debug(f'updating instance {instance} with data')
            [setattr(instance, field, value) for field, value in cleaned_data.items() if field != self.model_id_field]
            instance.save()

        sheet_row_processed.send(sender=self.model_cls, instance=instance, created=created, row_data=data)

        return instance, created

    def writeout_created_instance_ids(self, created_instances):
        cols_start, cols_end = self.sheet_range_cols
        start_row = created_instances[0][1]

        # find the column letter where the sheet ID lives
        sheet_id_ix = self.column_index(self.sheet_id_field)
        sheet_id_col_ix = BaseSheetInterface.convert_col_letter_to_number(cols_start) + sheet_id_ix
        sheet_id_col_name = BaseSheetInterface.convert_col_number_to_letter(sheet_id_col_ix)

        writeout_ranges = []
        writeout_data = []
        last_writeout_ix = 0
        # we segment the created instances into contiguous blocks of rows for the batch update
        for i in range(len(created_instances)):
            instance, row_ix = created_instances[i]
            last_row_ix = created_instances[i - 1][1] if i > 0 else row_ix

            # if we're at the end of a block of rows or on the last row, it delineates a writeout block
            if row_ix > last_row_ix + 1:
                writeout_ranges.append(BaseSheetInterface.get_sheet_range(
                    self.sheet_name,
                    f'{sheet_id_col_name}{start_row}:{sheet_id_col_name}{last_row_ix}'
                ))
                writeout_data.append(
                    [[str(getattr(instance, self.model_id_field))] for instance, noop in created_instances[last_writeout_ix:i]]
                )

                start_row = row_ix
                last_writeout_ix = i
            elif i == len(created_instances) - 1:
                writeout_ranges.append(BaseSheetInterface.get_sheet_range(
                    self.sheet_name,
                    f'{sheet_id_col_name}{start_row}:{sheet_id_col_name}{row_ix}'
                ))
                writeout_data.append(
                    [[str(getattr(instance, self.model_id_field))] for instance, noop in created_instances[last_writeout_ix:]]
                )

        logger.debug(f'writing out {writeout_ranges} data ranges')
        return self.writeout_batch(writeout_ranges, writeout_data)


class SheetSync(SheetPushInterface, SheetPullInterface):
    """ ability to 2-way sync data from/to a google sheet """
    def sheet_sync(self):
        self.pull_sheet()
        self.upsert_table()
