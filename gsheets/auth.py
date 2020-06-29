from django.urls import reverse
import re
import logging
import google.oauth2.credentials

logger = logging.getLogger(__name__)


def ensure_https(uri):
    """ takes a URI and ensures it has https protocol
    :param uri: `str`
    :return: `str`
    """
    if uri.startswith('http:'):
        return re.sub('^http', 'https', uri)

    return uri


def get_oauth_cb_url(request, cb_hostname=None):
    """ given a request object, gets the URL of the oauth callback
    :param request: `django.Request` instance
    :param cb_hostname: `str` if provided, the hostname of the callback URL (otherwise uses request context info)
    :return: `str` URL for oauth cb
    """
    path = reverse('gsheets_auth_success')
    callback_url = request.build_absolute_uri(path) if cb_hostname is None else f'https://{cb_hostname}{path}'
    return ensure_https(callback_url)


def get_gapi_credentials(access_credentials):
    """ gets an instance of google oauth2 credentials given an instance of our canonical AccessCredentials object
    :param access_credentials: `AccessCredentials`
    :return: `google.oauth2.credentials` instance
    """
    return google.oauth2.credentials.Credentials(
        token=access_credentials.token,
        refresh_token=access_credentials.refresh_token,
        token_uri=access_credentials.token_uri,
        client_id=access_credentials.client_id,
        client_secret=access_credentials.client_secret,
        scopes=access_credentials.parsed_scopes,
    )
