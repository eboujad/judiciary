"""
AuditMiddleware — captures IP and user-agent on every authenticated request.
Stored in thread-local so views can attach them to AuditLog entries.
"""
import threading

_thread_local = threading.local()


def get_current_request():
    return getattr(_thread_local, 'request', None)


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_local.request = request
        try:
            response = self.get_response(request)
        finally:
            _thread_local.request = None
        return response
