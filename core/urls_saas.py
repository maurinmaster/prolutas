from django.urls import path
from django.contrib.auth import views as auth_views
from . import views_saas, views

# URLs públicas do SaaS (sem slug de academia)
public_urlpatterns = [
    # Autenticação
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html', redirect_authenticated_user=True), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('login-redirect/', views.login_redirect, name='login_redirect'),
    
    # Páginas públicas
    path('', views_saas.pagina_planos, name='pagina_inicial_saas'),
    path('planos/', views_saas.pagina_planos, name='planos'),
    path('sobre/', views_saas.sobre, name='sobre'),
    path('contato/', views_saas.contato, name='contato'),
    
    # Cadastro de academias
    path('cadastro/', views_saas.cadastro_academia, name='cadastro_academia'),
    path('cadastro/<slug:plano_slug>/', views_saas.cadastro_academia, name='cadastro_academia_plano'),
    
    # Pagamento público (para academias recém-criadas)
    path('pagamento/', views_saas.pagamento, name='pagamento'),
    path('pagamento/sucesso/', views_saas.pagamento_sucesso_publico, name='pagamento_sucesso_publico'),
    path('pagamento/cancelado/', views_saas.pagamento_cancelado_publico, name='pagamento_cancelado_publico'),
    
    # Webhook do Stripe
    path('webhook/stripe/', views_saas.stripe_webhook, name='stripe_webhook'),
    
    # Nota: URLs do superadmin foram movidas para urls_superadmin.py
]

# URLs específicas da academia (com slug)
academia_urlpatterns = [
    # Pagamento
    path('pagamento/', views_saas.iniciar_pagamento, name='iniciar_pagamento'),
    path('pagamento/sucesso/', views_saas.pagamento_sucesso, name='pagamento_sucesso'),
    path('pagamento/cancelado/', views_saas.pagamento_cancelado, name='pagamento_cancelado'),
]