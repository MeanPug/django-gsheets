import django.dispatch

# dispatched when a row has been pulled from a spreadsheet and processed to create or update an instance
sheet_row_processed = django.dispatch.Signal()
