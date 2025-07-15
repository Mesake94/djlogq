from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
import json
from .async_logger import get_async_logger
from .models import LogEntry, LogLevel


@csrf_exempt
@require_http_methods(["POST"])
def log_endpoint(request):
    """Simple API endpoint for external logging."""
    try:
        data = json.loads(request.body)
        level = data.get('level', 'INFO')
        message = data.get('message', '')
        
        if not message:
            return JsonResponse({'error': 'Message is required'}, status=400)
        
        if level not in [choice[0] for choice in LogLevel.choices]:
            return JsonResponse({'error': 'Invalid log level'}, status=400)
        
        logger = get_async_logger()
        logger.log(level, message, extra_data=data.get('extra_data', {}))
        
        return JsonResponse({'status': 'success'})
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class LogAPIView(View):
    """Class-based view for more advanced logging operations."""
    
    def post(self, request):
        """Handle POST requests for logging."""
        try:
            data = json.loads(request.body)
            level = data.get('level', 'INFO')
            message = data.get('message', '')
            
            if not message:
                return JsonResponse({'error': 'Message is required'}, status=400)
            
            logger = get_async_logger()
            logger.log(
                level, 
                message, 
                user_id=data.get('user_id'),
                request_id=data.get('request_id'),
                extra_data=data.get('extra_data', {})
            )
            
            return JsonResponse({'status': 'success'})
        
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    def get(self, request):
        """Handle GET requests for retrieving recent logs."""
        try:
            limit = int(request.GET.get('limit', 100))
            level = request.GET.get('level')
            module = request.GET.get('module')
            
            query = LogEntry.objects.all()
            
            if level:
                query = query.filter(level=level)
            if module:
                query = query.filter(module__icontains=module)
            
            logs = query.order_by('-timestamp')[:limit]
            
            log_data = []
            for log in logs:
                log_data.append({
                    'id': log.id,
                    'timestamp': log.timestamp.isoformat(),
                    'level': log.level,
                    'message': log.message,
                    'module': log.module,
                    'function': log.function,
                    'line_number': log.line_number,
                    'user_id': log.user_id,
                    'request_id': log.request_id,
                    'extra_data': log.extra_data,
                })
            
            return JsonResponse({'logs': log_data})
        
        except ValueError:
            return JsonResponse({'error': 'Invalid limit parameter'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)