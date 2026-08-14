"""
Cookie-based JWT authentication.

Access/refresh tokens are delivered as httpOnly cookies (set in
accounts/views.py) instead of being handed back in the JSON response body
and stored in localStorage on the frontend. This closes off the JWT
straight to any XSS on the page being able to read/exfiltrate it via
`localStorage.getItem(...)`.

Trade-off this introduces: because the cookie now carries auth, and the
frontend origin differs from the API origin (see CORS_ALLOWED_ORIGINS),
the cookies must be sent with SameSite=None; Secure in production so the
browser will attach them cross-site at all - which on its own would
reopen a CSRF hole (any other site can trigger a cross-site request and
the browser will still attach our auth cookie). CsrfCookieCheck below
implements the standard double-submit-cookie mitigation for that: a
second, JS-readable (non-httpOnly) `csrf_token` cookie is set alongside
the auth cookies, and every unsafe-method (POST/PUT/PATCH/DELETE) request
must echo that value back in an `X-CSRF-Token` header. A cross-site
attacker can make the browser send the cookie automatically, but can't
read the cookie's value to also set the matching header (browsers block
cross-origin reads of Set-Cookie'd values), so the two won't match.
"""

import secrets

from django.conf import settings
from rest_framework import exceptions
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed


CSRF_COOKIE_NAME = 'csrf_token'
CSRF_HEADER_NAME = 'HTTP_X_CSRF_TOKEN'
SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


class CookieJWTAuthentication(JWTAuthentication):
    """Reads the access token from the `access_token` httpOnly cookie
    instead of (or in addition to, for backward compatibility during
    rollout) the `Authorization: Bearer` header."""

    def authenticate(self, request):
        cookie_name = settings.SIMPLE_JWT.get('AUTH_COOKIE_ACCESS', 'access_token')
        raw_token = request.COOKIES.get(cookie_name)

        if raw_token is None:
            # Fall back to the standard Authorization-header flow. Kept so
            # server-to-server / mobile-app callers that can't use cookies
            # (and any in-flight requests from clients that haven't
            # refreshed to the cookie-based frontend yet) still work.
            return super().authenticate(request)

        validated_token = self.get_validated_token(raw_token)
        user = self.get_user(validated_token)

        # Enforce the CSRF double-submit check for any unsafe method that
        # authenticated via the cookie (Authorization-header requests are
        # exempt - a header can't be silently attached by a third-party
        # site the way a cookie can, so they aren't CSRF-able the same way).
        if request.method not in SAFE_METHODS:
            csrf_cookie = request.COOKIES.get(CSRF_COOKIE_NAME)
            csrf_header = request.META.get(CSRF_HEADER_NAME)
            if not csrf_cookie or not csrf_header or not secrets.compare_digest(csrf_cookie, csrf_header):
                raise exceptions.PermissionDenied('CSRF check failed: missing or mismatched X-CSRF-Token header.')

        return user, validated_token
