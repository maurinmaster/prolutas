from django.urls import path
from . import views

app_name = 'vendas'

urlpatterns = [
    # Páginas principais
    path('', views.pagina_inicial, name='pagina_inicial'),
    path('planos/', views.planos_precos, name='planos_precos'),
    path('sobre/', views.sobre, name='sobre'),
    path('contato/', views.contato, name='contato'),
    path('politica-privacidade/', views.politica_privacidade, name='politica_privacidade'),
    path('termos-uso/', views.termos_uso, name='termos_uso'),
    
    # Captura de leads
    path('capturar-lead/', views.capturar_lead, name='capturar_lead'),
    
    # Checkout e pagamento
    path('checkout/<slug:plano_slug>/', views.checkout, name='checkout'),
    path('criar-sessao-pagamento/', views.criar_sessao_pagamento, name='criar_sessao_pagamento'),
    path('sucesso/', views.sucesso_pagamento, name='sucesso_pagamento'),
    path('cancelado/', views.cancelado_pagamento, name='cancelado_pagamento'),
    
    # Webhook do Stripe
    path('webhook/stripe/', views.webhook_stripe, name='webhook_stripe'),
]
