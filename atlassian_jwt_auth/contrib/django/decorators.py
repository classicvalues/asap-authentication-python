from functools import wraps

from django.conf import settings
from django.http.response import HttpResponse
from django.utils import six

import atlassian_jwt_auth
from .utils import parse_jwt, verify_issuers
from ..server import _requires_asap


def requires_asap(issuers=None):
    """Decorator for Django endpoints to require ASAP

    :param list issuers: *required The 'iss' claims that this endpoint is from.
    """
    def requires_asap_decorator(func):
        @wraps(func)
        def requires_asap_wrapper(request, *args, **kwargs):
            verifier = _get_verifier()
            auth_header = request.META.get('HTTP_AUTHORIZATION', b'')
            # Per PEP-3333, headers must be in ISO-8859-1 or use an RFC-2047
            # MIME encoding. We don't really care about MIME encoded
            # headers, but some libraries allow sending bytes (Django tests)
            # and some (requests) always send str so we need to convert if
            # that is the case to properly support Python 3.
            if isinstance(auth_header, six.string_types):
                auth_header = auth_header.encode(encoding='iso-8859-1')
            auth = auth_header.split(b' ')
            result = _requires_asap(
                verifier=verifier,
                auth=auth,
                parse_jwt_func=parse_jwt,
                response_class=HttpResponse,
                asap_claim_holder=request,
                verify_issuers_func=verify_issuers,
                issuers=issuers,
            )
            if result is None:
                return func(request, *args, **kwargs)
            return result

        return requires_asap_wrapper
    return requires_asap_decorator


def _get_verifier():
    """Return a verifier for ASAP JWT tokens based on settings"""
    retriever_cls = getattr(settings, 'ASAP_KEY_RETRIEVER_CLASS',
                            atlassian_jwt_auth.HTTPSPublicKeyRetriever)
    retriever = retriever_cls(
        base_url=getattr(settings, 'ASAP_PUBLICKEY_REPOSITORY')
    )
    return atlassian_jwt_auth.JWTAuthVerifier(retriever)
