"""
Centralised exception handling — returns consistent JSON error shapes.
"""
import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


def judiciary_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        # Standardise the error envelope
        error_data = {
            'error': True,
            'status_code': response.status_code,
        }
        if isinstance(response.data, dict):
            error_data['detail'] = response.data.get('detail', response.data)
            error_data['fields'] = {
                k: v for k, v in response.data.items() if k != 'detail'
            } or None
        else:
            error_data['detail'] = response.data

        response.data = error_data

    else:
        # Unhandled exception — 500
        logger.exception("Unhandled exception in view: %s", exc)
        response = Response(
            {
                'error': True,
                'status_code': 500,
                'detail': 'An internal server error occurred.',
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return response
