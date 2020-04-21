from django.urls import path
from .views import OAuthSuccessView, AuthorizeView

urlpatterns = [
    path('gsheets/authorize/', AuthorizeView.as_view(), name='gsheets_authorize'),
    path('gsheets/auth-success/', OAuthSuccessView.as_view(), name='gsheets_auth_success')
]
