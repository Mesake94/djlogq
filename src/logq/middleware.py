import uuid
from django.utils.deprecation import MiddlewareMixin
from .async_logger import get_async_logger
from django.conf import settings

class AsyncLoggingMiddleware(MiddlewareMixin):
    """
    Middleware that automatically logs request information and adds request_id to the request.
    """
    
    def process_request(self, request):
        # Check if request path is in ignore paths
        ignore_paths = getattr(settings, 'ASYNC_LOGGING_CONFIG', {}).get('IGNORE_PATHS', [])
        if any(request.path.startswith(path) for path in ignore_paths):
            return None
        
        # Generate unique request ID
        request.request_id = str(uuid.uuid4())
        
        # Get user ID if authenticated
        user_id = None
        if hasattr(request, 'user') and request.user.is_authenticated:
            user_id = request.user.id
        
        # Log request start
        logger = get_async_logger()
        logger.info(
            f"Request started: {request.method} {request.path}",
            request_id=request.request_id,
            user_id=user_id,
            extra_data={
                'method': request.method,
                'path': request.path,
                'query_params': dict(request.GET),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'ip_address': self._get_client_ip(request),
            }
        )
    
    def process_response(self, request, response):
        # Check if request path is in ignore paths
        ignore_paths = getattr(settings, 'ASYNC_LOGGING_CONFIG', {}).get('IGNORE_PATHS', [])
        if any(request.path.startswith(path) for path in ignore_paths):
            return response
        
        # Get user ID if authenticated
        user_id = None
        if hasattr(request, 'user') and request.user.is_authenticated:
            user_id = request.user.id
        
        # Log request completion
        logger = get_async_logger()
        logger.info(
            f"Request completed: {request.method} {request.path} - {response.status_code}",
            request_id=getattr(request, 'request_id', 'unknown'),
            user_id=user_id,
            extra_data={
                'status_code': response.status_code,
                'content_length': len(response.content) if hasattr(response, 'content') else 0,
            }
        )
        
        return response
    
    def process_exception(self, request, exception):
        # Check if request path is in ignore paths
        ignore_paths = getattr(settings, 'ASYNC_LOGGING_CONFIG', {}).get('IGNORE_PATHS', [])
        if any(request.path.startswith(path) for path in ignore_paths):
            return None
        
        # Get user ID if authenticated
        user_id = None
        if hasattr(request, 'user') and request.user.is_authenticated:
            user_id = request.user.id
        
        # Log exception
        logger = get_async_logger()
        logger.exception(
            f"Request exception: {request.method} {request.path}",
            exc_info=str(exception),
            request_id=getattr(request, 'request_id', 'unknown'),
            user_id=user_id,
            extra_data={
                'exception_type': type(exception).__name__,
                'exception_args': str(exception.args),
            }
        )
    
    def _get_client_ip(self, request):
        """Get the client's IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip