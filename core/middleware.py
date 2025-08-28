from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.models import AnonymousUser
from django.http import Http404
from .models import Academia, set_current_academia
import re

class MultiTenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # URLs que não precisam de verificação de academia (públicas)
        excluded_urls = [
            '/admin/',
            '/admin-saas/',
            '/superadmin/',  # Área administrativa do SaaS
            '/api/',
            '/static/',
            '/media/',
            '/favicon.ico',
            '/cadastro/',
            '/login/',
            '/logout/',
            '/login-redirect/',  # Redirecionamento após login
            '/login-publico/',
            '/planos/',
            '/sobre/',
            '/contato/',
            '/webhook/',
            '/pagamento/',
        ]
        
        # Verifica se a URL atual está na lista de exclusões
        if any(request.path.startswith(url) for url in excluded_urls):
            return self.get_response(request)
        
        # Extrai o slug da academia da URL usando regex
        # Padrão: /{slug}/... ou /{slug} 
        slug_pattern = r'^/([a-zA-Z0-9-_]+)/'
        match = re.match(slug_pattern, request.path)
        
        if match:
            slug = match.group(1)
            
            # Verifica se o slug existe e a academia está ativa
            try:
                academia = Academia.objects.get(slug=slug, ativa=True)
                request.academia = academia
                request.academia_slug = slug
                
                # Define a academia no contexto da thread para filtros automáticos
                set_current_academia(academia)
                
                # Remove o slug da URL para processamento interno
                # request.path_info = request.path[len(slug) + 1:] or '/'
                # Comentado para evitar redirecionamento duplo no dashboard
                
            except Academia.DoesNotExist:
                # Academia não encontrada ou inativa
                raise Http404("Academia não encontrada ou inativa")
        else:
            # URL sem slug - redireciona para página pública
            return redirect('/planos/')
        
        response = self.get_response(request)
        return response

class AssinaturaMiddleware:
    """Middleware legado - mantido para compatibilidade"""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # URLs que não precisam de verificação de academia
        excluded_urls = [
            '/login/',
            '/logout/',
            '/admin/',
            '/api/',
            '/static/',
            '/media/',
            '/sem-academia/',
            '/favicon.ico',
        ]
        
        # Verifica se a URL atual está na lista de exclusões
        if any(request.path.startswith(url) for url in excluded_urls):
            return self.get_response(request)
        
        # Verifica se o usuário está autenticado e não é superuser
        if request.user.is_authenticated and not request.user.is_superuser:
            try:
                # Tenta obter a academia do usuário
                academia = Academia.objects.get(dono=request.user)
                request.academia = academia
            except Academia.DoesNotExist:
                # Se não encontrar academia, redireciona para página de erro
                if request.path != '/sem-academia/':
                    return redirect('sem_academia')
        
        response = self.get_response(request)
        return response


