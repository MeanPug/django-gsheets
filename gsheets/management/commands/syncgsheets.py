from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.apps import apps
from gsheets import mixins


class Command(BaseCommand):
    help = 'Finds all models mixing in a Sheet syncing mixin and executes the sync'

    def handle(self, *args, **options):
        for model in self.find_syncable_models():
            if issubclass(model, mixins.SheetSyncableMixin):
                model.sync_sheet()
            elif issubclass(model, mixins.SheetPullableMixin):
                model.pull_sheet()
            elif issubclass(model, mixins.SheetPushableMixin):
                model.push_to_sheet()
            else:
                raise CommandError(f'model {model} doesnt subclass a viable mixin for sync')

            self.stdout.write(self.style.SUCCESS(f'Successfully synced model {model}'))

        self.stdout.write(self.style.SUCCESS('Successfully finished sync'))

    def find_syncable_models(self):
        app_models = []
        for app in settings.INSTALLED_APPS:
            try:
                models = apps.get_app_config(app).get_models()
            except LookupError:
                continue

            app_models += [m for m in models if issubclass(m, mixins.BaseGoogleSheetMixin)]

        self.stdout.write(f'found {len(app_models)} syncable models')

        return app_models
