from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # URL de Cadastro de Academia
    path('cadastro/', views.cadastro_academia, name='cadastro_academia'),

    # URLs de Autenticação
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html', redirect_authenticated_user=True), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    
    # URL do Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # URLs do CRUD de Alunos
    path('aluno/adicionar/', views.aluno_add, name='aluno_add'),
    path('aluno/<int:pk>/editar/', views.aluno_edit, name='aluno_edit'),
    path('aluno/<int:pk>/excluir/', views.aluno_delete, name='aluno_delete'),

    # URLs do CRUD de Turmas
    path('turma/adicionar/', views.turma_add, name='turma_add'),
    path('turma/<int:pk>/editar/', views.turma_edit, name='turma_edit'),
    path('turma/<int:pk>/excluir/', views.turma_delete, name='turma_delete'),

    # URLs de Presença
    path('presenca/', views.pagina_presenca, name='pagina_presenca'),
    path('presenca/marcar/<int:aluno_pk>/', views.marcar_presenca_geral, name='marcar_presenca_geral'),

    # --------------------------------------------------------------------------
    # URLs FINANCEIRAS (VERSÃO CORRIGIDA E ATUALIZADA)
    # --------------------------------------------------------------------------
    path('financeiro/', views.pagina_financeiro, name='pagina_financeiro'),
    # A URL antiga 'gerar-mensalidade' foi substituída por 'criar-assinatura'
    path('financeiro/criar-assinatura/<int:aluno_pk>/', views.criar_assinatura, name='criar_assinatura'),
    # A URL de pagamento agora usa 'fatura_pk'
    path('financeiro/registrar-pagamento/<int:fatura_pk>/', views.registrar_pagamento, name='registrar_pagamento'),
    # --------------------------------------------------------------------------

    # URLs de Cadastros Auxiliares
    path('cadastros/', views.gerenciar_cadastros, name='gerenciar_cadastros'),
    path('cadastros/modalidade/<int:pk>/deletar/', views.deletar_modalidade, name='deletar_modalidade'),
    path('cadastros/professor/<int:pk>/deletar/', views.deletar_professor, name='deletar_professor'),

    # URLs de Planos
    path('cadastros/planos/', views.gerenciar_planos, name='gerenciar_planos'),
    path('cadastros/planos/<int:pk>/deletar/', views.deletar_plano, name='deletar_plano'),

    # URLs de Dias Não Letivos
    path('config/dias-nao-letivos/', views.gerenciar_dias_nao_letivos, name='gerenciar_dias_nao_letivos'),
    path('config/dias-nao-letivos/<int:pk>/deletar/', views.deletar_dia_nao_letivo, name='deletar_dia_nao_letivo'),
    path('financeiro/fatura/<int:fatura_pk>/alterar-vencimento/', views.alterar_vencimento_fatura, name='alterar_vencimento_fatura'),
    path('financeiro/assinatura/<int:assinatura_pk>/cancelar/', views.cancelar_assinatura, name='cancelar_assinatura'),

    path('api/ia/ask/', views.AgenteIAAPIView.as_view(), name='ask_ia_agent'),
    path('config/whatsapp/', views.configuracao_whatsapp, name='configuracao_whatsapp'),
    path('config/whatsapp/conexao/', views.whatsapp_conexao, name='whatsapp_conexao'),

    path('relatorios/frequencia/', views.relatorio_frequencia, name='relatorio_frequencia'),
    path('relatorios/financeiro/', views.relatorio_financeiro, name='relatorio_financeiro'),

    path('cadastros/graduacoes/', views.gerenciar_graduacoes, name='gerenciar_graduacoes'),
    path('cadastros/graduacoes/<int:pk>/deletar/', views.deletar_graduacao, name='deletar_graduacao'),

    #Urls de Exames
    path('graduacao/exames/', views.gerenciar_exames, name='gerenciar_exames'),
    path('graduacao/alunos-aptos/', views.relatorio_alunos_aptos, name='relatorio_alunos_aptos'),
    path('cadastros/graduacoes/<int:pk>/editar/', views.graduacao_edit, name='graduacao_edit'),

    path('aluno/<int:pk>/', views.aluno_detalhe, name='aluno_detalhe'), # NOVA URL
    path('graduacao/exames/<int:pk>/', views.detalhe_exame, name='detalhe_exame'),
    path('graduacao/exames/<int:exame_pk>/convidar/', views.convidar_alunos_exame, name='convidar_alunos_exame'),
    path('graduacao/inscricao/<int:inscricao_pk>/status/<str:novo_status>/', views.atualizar_status_inscricao, name='atualizar_status_inscricao'),
    path('graduacao/exames/<int:pk>/deletar/', views.deletar_exame, name='deletar_exame'),
    path('graduacao/inscricao/<int:inscricao_pk>/resultado/', views.registrar_resultado_exame, name='registrar_resultado_exame'),
    path('relatorios/mensagens/', views.relatorio_mensagens, name='relatorio_mensagens'),

]