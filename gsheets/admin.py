from django.contrib import admin
from .models import AccessCredentials


@admin.register(AccessCredentials)
class AccessCredentialsAdmin(admin.ModelAdmin):
    fields = ('token', 'refresh_token', 'token_uri', 'scopes', 'created_time',)
    readonly_fields = ('token_uri', 'scopes', 'created_time')
