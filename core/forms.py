from django import forms
import os
from django import forms
from django.conf import settings
from django.utils.safestring import mark_safe
from django.contrib.auth.forms import UserCreationForm
from .models import (
    Academia, Aluno, Turma, Horario, Modalidade, Professor,
    Plano, Assinatura, Fatura, DiaNaoLetivo, Graduacao, ExameGraduacao, HistoricoGraduacao, InscricaoExame
)

# -----------------------------------------------------------------------------
# FORMULÁRIOS DE CADASTRO INICIAL
# -----------------------------------------------------------------------------

class CustomUserCreationForm(UserCreationForm):
    """ Formulário para criar um novo usuário (dono da academia). """
    class Meta(UserCreationForm.Meta):
        fields = UserCreationForm.Meta.fields + ('first_name', 'last_name', 'email')

class AcademiaForm(forms.ModelForm):
    """ Formulário para os dados da academia. """
    class Meta:
        model = Academia
        exclude = ['dono']

# -----------------------------------------------------------------------------
# FORMULÁRIOS DAS ENTIDADES PRINCIPAIS
# -----------------------------------------------------------------------------

class AlunoForm(forms.ModelForm):
    class Meta:
        model = Aluno
        fields = [
            'foto',
            'nome_completo',
            'data_nascimento',
            'cpf',
            'contato',
            'nome_responsavel',
            'contato_responsavel',
            'observacoes_medicas',
            'ativo',
            'dia_vencimento',
            'receber_notificacoes',
        ]
        widgets = {
            'data_nascimento': forms.DateInput(attrs={'type': 'date'}),
            'observacoes_medicas': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        # Este __init__ foi removido em passos anteriores, garantindo que não esteja mais aqui.
        # Se ele ainda existir no seu código, pode apagá-lo.
        super().__init__(*args, **kwargs)

class TurmaForm(forms.ModelForm):
    alunos = forms.ModelMultipleChoiceField(
        queryset=Aluno.objects.none(),
        widget=forms.SelectMultiple(attrs={'class': 'select2-widget', 'style': 'width: 100%'}),
        required=False,
        label="Alunos"
    )
    class Meta:
        model = Turma
        fields = ['modalidade', 'professor', 'limite_alunos', 'ativa', 'alunos']
    
    def __init__(self, *args, **kwargs):
        academia = kwargs.pop('academia', None)
        super().__init__(*args, **kwargs)
        if academia:
            self.fields['modalidade'].queryset = Modalidade.objects.filter(academia=academia)
            self.fields['professor'].queryset = Professor.objects.filter(academia=academia)
            self.fields['alunos'].queryset = Aluno.objects.filter(academia=academia, ativo=True)

class HorarioForm(forms.ModelForm):
    class Meta:
        model = Horario
        fields = ['dias_semana', 'horario_inicio', 'horario_fim']
        widgets = {
            'dias_semana': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Seg, Qua, Sex'}),
            'horario_inicio': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'horario_fim': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        }

# -----------------------------------------------------------------------------
# FORMULÁRIOS FINANCEIROS (NOVA ESTRUTURA)
# -----------------------------------------------------------------------------

class PlanoForm(forms.ModelForm):
    class Meta:
        model = Plano
        fields = ['nome', 'valor', 'duracao_meses', 'descricao']
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 2}),
        }

class AssinaturaForm(forms.ModelForm):
    """ Formulário para criar uma nova assinatura para um aluno. """
    class Meta:
        model = Assinatura
        fields = ['plano', 'data_inicio']
        widgets = {
            'data_inicio': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        academia = kwargs.pop('academia', None)
        super().__init__(*args, **kwargs)
        if academia:
            self.fields['plano'].queryset = Plano.objects.filter(academia=academia)

class RegistrarPagamentoForm(forms.ModelForm):
    """ Formulário para registrar o pagamento de uma fatura existente. """
    class Meta:
        model = Fatura  # Apontando para o novo modelo Fatura
        fields = ['data_pagamento']
        widgets = {
            'data_pagamento': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['data_pagamento'].label = "Data em que o pagamento foi realizado"
        self.fields['data_pagamento'].required = True

class AlterarVencimentoForm(forms.ModelForm):
    """ Formulário para alterar a data de vencimento de uma fatura existente. """
    class Meta:
        model = Fatura
        fields = ['data_vencimento']
        widgets = {
            'data_vencimento': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['data_vencimento'].label = "Nova Data de Vencimento"

# -----------------------------------------------------------------------------
# FORMULÁRIOS DE CADASTROS AUXILIARES
# -----------------------------------------------------------------------------

class ModalidadeForm(forms.ModelForm):
    class Meta:
        model = Modalidade
        fields = ['nome', 'descricao']
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 3}),
        }

class ProfessorForm(forms.ModelForm):
    class Meta:
        model = Professor
        fields = ['nome_completo', 'contato', 'observacoes']
        widgets = {
            'observacoes': forms.Textarea(attrs={'rows': 3}),
        }

class DiaNaoLetivoForm(forms.ModelForm):
    class Meta:
        model = DiaNaoLetivo
        fields = ['data', 'descricao']
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date'}),
        }

# -----------------------------------------------------------------------------
# FORMULÁRIOS DE CONFIGURAÇÃO WHATSAPP
# -----------------------------------------------------------------------------
class ConfiguracaoWhatsAppForm(forms.ModelForm):
    class Meta:
        model = Academia
        # Incluímos apenas os campos que queremos que o usuário edite nesta página
        fields = [
            'whatsapp_numero',
            'notificar_inadimplencia',
            'notificar_boas_vindas',
            'notificar_faltas',
            'notificar_graduacao'
        ]

# Criamos um widget customizado para renderizar a imagem no radio button
class ImageRadioSelect(forms.RadioSelect):
    def render(self, name, value, attrs=None, renderer=None):
        html = super().render(name, value, attrs, renderer)
        return mark_safe(html.replace('</label>', '</span></label>').replace('">', '"><span class="icon-label">'))


class GraduacaoForm(forms.ModelForm):
    # Definimos o campo de ícones manualmente
    icone_arquivo = forms.ChoiceField(
        widget=ImageRadioSelect,
        label="Ícone da Graduação"
    )

    class Meta:
        model = Graduacao
        # Note que 'icone_arquivo' foi removido desta lista, pois o definimos manualmente acima
        fields = ['modalidade', 'nome', 'ordem', 'tempo_minimo_meses', 'pre_requisitos']
        widgets = {
            'pre_requisitos': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        academia = kwargs.pop('academia', None)
        super().__init__(*args, **kwargs)

        # Filtra as modalidades
        if academia:
            self.fields['modalidade'].queryset = Modalidade.objects.filter(academia=academia)

        # --- Lógica para buscar os ícones ---
        icon_choices = []
        try:
            # Constrói o caminho para a pasta de ícones
            icon_dir = os.path.join(settings.BASE_DIR, 'core', 'static', 'core', 'img', 'graduacoes')
            
            # Lista todos os arquivos na pasta
            files = os.listdir(icon_dir)
            
            # Cria as opções para o formulário
            for filename in sorted(files):
                # O valor salvo no banco será o nome do arquivo
                choice_value = filename
                # O que será mostrado na tela será a imagem + nome do arquivo
                choice_label = mark_safe(f"<img src='/static/core/img/graduacoes/{filename}' width='24' class='me-2' /> {filename}")
                icon_choices.append((choice_value, choice_label))

        except FileNotFoundError:
            icon_choices.append(("", "Pasta de ícones não encontrada"))

        # Define as opções do campo 'icone_arquivo'
        self.fields['icone_arquivo'].choices = icon_choices

class ExameGraduacaoForm(forms.ModelForm):
    class Meta:
        model = ExameGraduacao
        fields = ['modalidade', 'data_exame', 'local', 'responsavel']
        widgets = {
            'data_exame': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        }

    def __init__(self, *args, **kwargs):
        academia = kwargs.pop('academia', None)
        super().__init__(*args, **kwargs)
        if academia:
            # Filtra os campos para mostrar apenas opções da academia do usuário
            self.fields['modalidade'].queryset = Modalidade.objects.filter(academia=academia)
            self.fields['responsavel'].queryset = Professor.objects.filter(academia=academia)

class HistoricoGraduacaoForm(forms.ModelForm):
    class Meta:
        model = HistoricoGraduacao
        fields = ['graduacao', 'data_promocao', 'observacoes']
        widgets = {
            'data_promocao': forms.DateInput(attrs={'type': 'date'}),
            'observacoes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        academia = kwargs.pop('academia', None)
        super().__init__(*args, **kwargs)
        if academia:
            # Mostra apenas graduações da academia do usuário
            self.fields['graduacao'].queryset = Graduacao.objects.filter(academia=academia)

class ReprovacaoForm(forms.ModelForm):
    """ Formulário para adicionar observações ao reprovar um aluno. """
    class Meta:
        model = InscricaoExame
        fields = ['observacoes']
        widgets = {
            'observacoes': forms.Textarea(attrs={'rows': 4}),
        }
        labels = {
            'observacoes': 'Observações (pontos a melhorar para o próximo exame)'
        }