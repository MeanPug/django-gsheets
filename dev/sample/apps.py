from django.apps import AppConfig


class SampleConfig(AppConfig):
    name = 'sample'

    def ready(self):
        import sample.signals
