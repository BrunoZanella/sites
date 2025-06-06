from django.utils.deprecation import MiddlewareMixin
import re

class MobileDetectionMiddleware(MiddlewareMixin):
    """
    Middleware para detectar se o usuário está usando um dispositivo móvel
    """
    def process_request(self, request):
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Padrões comuns de user agents de dispositivos móveis
        mobile_patterns = [
            'Mobile', 'Android', 'iPhone', 'iPad', 'Windows Phone',
            'BlackBerry', 'Opera Mini', 'IEMobile'
        ]
        
        # Verifica se o user agent contém algum dos padrões móveis
        is_mobile = any(pattern in user_agent for pattern in mobile_patterns)
        
        # Adiciona a informação ao objeto request
        request.user_agent = type('UserAgent', (), {'is_mobile': is_mobile})
        
        return None
