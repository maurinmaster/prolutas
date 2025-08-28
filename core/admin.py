from django.contrib import admin
from .models import (
    Academia, Aluno, Modalidade, Professor, Turma, Horario,
    Plano, Assinatura, Fatura,  # Nossos novos modelos financeiros
    Presenca, DiaNaoLetivo
)

# --- INLINES ---
class HorarioInline(admin.TabularInline):
    model = Horario
    extra = 1

# --- ADMINS PRINCIPAIS ---

@admin.register(Academia)
class AcademiaAdmin(admin.ModelAdmin):
    list_display = ('nome_fantasia', 'cnpj', 'dono', 'data_cadastro')
    search_fields = ('nome_fantasia', 'cnpj')

@admin.register(Aluno)
class AlunoAdmin(admin.ModelAdmin):
    list_display = ('nome_completo', 'academia', 'contato', 'ativo')
    search_fields = ('nome_completo', 'cpf')
    list_filter = ('academia', 'ativo')
    list_per_page = 20

@admin.register(Turma)
class TurmaAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'professor', 'ativa')
    list_filter = ('academia', 'modalidade', 'professor', 'ativa')
    filter_horizontal = ('alunos',)
    inlines = [HorarioInline]

# --- ADMINS DE CADASTROS AUXILIARES ---

@admin.register(Modalidade)
class ModalidadeAdmin(admin.ModelAdmin):
    list_display = ('nome', 'academia')
    list_filter = ('academia',)

@admin.register(Professor)
class ProfessorAdmin(admin.ModelAdmin):
    list_display = ('nome_completo', 'academia', 'contato')
    list_filter = ('academia',)

@admin.register(DiaNaoLetivo)
class DiaNaoLetivoAdmin(admin.ModelAdmin):
    list_display = ('data', 'descricao', 'academia')
    list_filter = ('academia',)
    date_hierarchy = 'data'

# --- ADMINS FINANCEIROS ---

@admin.register(Plano)
class PlanoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'valor', 'duracao_meses', 'academia')
    list_filter = ('academia',)

@admin.register(Assinatura)
class AssinaturaAdmin(admin.ModelAdmin):
    list_display = ('aluno', 'plano', 'status', 'data_inicio')
    list_filter = ('academia', 'plano', 'status')
    search_fields = ('aluno__nome_completo',)

@admin.register(Fatura)
class FaturaAdmin(admin.ModelAdmin):
    list_display = ('get_aluno', 'valor', 'data_vencimento', 'data_pagamento', 'status')
    list_filter = ('academia', 'data_vencimento', 'data_pagamento')
    search_fields = ('assinatura__aluno__nome_completo',)
    
    # Função para mostrar o nome do aluno na lista, já que a Fatura se liga à Assinatura
    @admin.display(description='Aluno', ordering='assinatura__aluno')
    def get_aluno(self, obj):
        return obj.assinatura.aluno

# --- ADMINS DE REGISTROS ---

@admin.register(Presenca)
class PresencaAdmin(admin.ModelAdmin):
    list_display = ('aluno', 'data', 'turma')
    list_filter = ('turma', 'data', 'academia')
    search_fields = ('aluno__nome_completo',)





