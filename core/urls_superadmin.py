from django.urls import path
from . import views_saas

# URLs exclusivas do superadmin (área administrativa do SaaS)
urlpatterns = [
    # Dashboard principal do superadmin
    path('', views_saas.admin_dashboard, name='superadmin_dashboard'),
    
    # Gestão de academias
    path('academias/', views_saas.admin_academias, name='superadmin_academias'),
    
    # Gestão de planos
    path('planos/', views_saas.admin_planos, name='superadmin_planos'),
    
    # Logs do sistema
    path('logs/', views_saas.admin_logs, name='superadmin_logs'),
    
    # Configurações do sistema
    path('configuracoes/', views_saas.admin_configuracoes, name='superadmin_configuracoes'),
    
    # Relatórios
    path('relatorios/', views_saas.admin_relatorios, name='superadmin_relatorios'),
    
    # Outras funcionalidades serão adicionadas conforme necessário
]