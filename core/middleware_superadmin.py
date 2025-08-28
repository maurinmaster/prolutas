from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth.models import User

class SuperAdminMiddleware:
    """
    Middleware específico para a área administrativa do SaaS.
    Garante que apenas superusuários tenham acesso ao /superadmin/
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Verifica se a requisição é para a área do superadmin
        if request.path.startswith('/superadmin/'):
            # Se não estiver autenticado, redireciona para login
            if not request.user.is_authenticated:
                return redirect(f"{reverse('login')}?next={request.path}")
            
            # Se não for superusuário, nega acesso
            if not request.user.is_superuser:
                from django.http import HttpResponseForbidden
                return HttpResponseForbidden(
                    "<h1>Acesso Negado</h1>"
                    "<p>Você não tem permissão para acessar esta área.</p>"
                    "<p>Esta é a área administrativa do SaaS, restrita a superusuários.</p>"
                )
            
            # Adiciona contexto específico do superadmin
            request.is_superadmin_area = True
        else:
            request.is_superadmin_area = False
        
        response = self.get_response(request)
        return response