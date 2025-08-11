from datetime import date
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User

# -----------------------------------------------------------------------------
# MODELOS PRINCIPAIS E CADASTROS AUXILIARES
# -----------------------------------------------------------------------------

class Academia(models.Model):
    """ Representa uma academia que utiliza o sistema (o 'inquilino' do SaaS). """
    nome_fantasia = models.CharField(max_length=100, help_text="Nome popular da academia")
    razao_social = models.CharField(max_length=100, help_text="Nome legal da empresa")
    cnpj = models.CharField(max_length=18, unique=True, help_text="CNPJ da academia (formato XX.XXX.XXX/XXXX-XX)")
    telefone = models.CharField(max_length=20, blank=True, null=True, help_text="Telefone de contato principal")
    endereco = models.CharField(max_length=255, blank=True, null=True, help_text="Endereço completo da academia")
    dono = models.OneToOneField(User, on_delete=models.PROTECT, related_name='academia_dono')
    data_cadastro = models.DateTimeField(auto_now_add=True)

    # --- NOVOS CAMPOS DE CONFIGURAÇÃO WHATSAPP ---
    whatsapp_numero = models.CharField(
        max_length=20, blank=True, null=True,
        help_text="Número de celular com código do país (ex: 5575999998888) que enviará as mensagens."
    )
    notificar_inadimplencia = models.BooleanField(default=False, help_text="Ativar lembretes para faturas vencidas.")
    notificar_boas_vindas = models.BooleanField(default=False, help_text="Ativar mensagens de boas-vindas para novos alunos.")
    notificar_faltas = models.BooleanField(default=False, help_text="Ativar mensagens para alunos com baixa frequência.")
    notificar_graduacao = models.BooleanField(default=False, help_text="Ativar convites e parabenizações de exames de graduação.")

    def __str__(self):
        return self.nome_fantasia

class Aluno(models.Model):
    """ Representa um aluno matriculado em uma academia. """
    academia = models.ForeignKey(Academia, on_delete=models.CASCADE, related_name='alunos')
    nome_completo = models.CharField(max_length=100, help_text="Nome completo do aluno")
    data_nascimento = models.DateField(help_text="Data de nascimento do aluno")
    cpf = models.CharField(max_length=14, blank=True, null=True, help_text="CPF do aluno (formato XXX.XXX.XXX-XX)")
    contato = models.CharField(max_length=20, help_text="Telefone ou email de contato do aluno")
    foto = models.ImageField(upload_to='alunos_fotos/', blank=True, null=True, help_text="Foto do aluno")
    nome_responsavel = models.CharField(max_length=100, blank=True, null=True, help_text="Nome do responsável (se o aluno for menor de idade)")
    contato_responsavel = models.CharField(max_length=20, blank=True, null=True, help_text="Contato do responsável")
    observacoes_medicas = models.TextField(blank=True, null=True, help_text="Restrições ou observações médicas importantes")
    ativo = models.BooleanField(default=True, help_text="Indica se o aluno está com a matrícula ativa")
    data_matricula = models.DateField(auto_now_add=True)
    dia_vencimento = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Dia do mês para o vencimento da mensalidade (ex: 5, 10, 15)."
    )
    receber_notificacoes = models.BooleanField(
        default=True,
        help_text="Se desmarcado, o aluno não receberá nenhuma notificação automática via WhatsApp."
    )

    class Meta:
        ordering = ['nome_completo']

    def __str__(self):
        return f"{self.nome_completo} ({self.academia.nome_fantasia})"

    @property
    def graduacao_atual(self):
        """ Retorna a graduação mais recente do aluno com base no histórico. """
        historico_recente = self.historico_graduacoes.order_by('-data_promocao').first()
        if historico_recente:
            return historico_recente.graduacao
        return None

    @property
    def graduacao_atual(self):
        """ Retorna a graduação mais recente do aluno com base no histórico. """
        historico_recente = self.historico_graduacoes.order_by('-data_promocao').first()
        if historico_recente:
            return historico_recente.graduacao
        return None

class Professor(models.Model):
    """ Representa um professor/instrutor da academia. """
    academia = models.ForeignKey(Academia, on_delete=models.CASCADE, related_name='professores')
    nome_completo = models.CharField(max_length=100)
    contato = models.CharField(max_length=20, blank=True, null=True)
    observacoes = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Professor"
        verbose_name_plural = "Professores"

    def __str__(self):
        return self.nome_completo

class Modalidade(models.Model):
    """ Representa uma modalidade de luta oferecida pela academia. """
    academia = models.ForeignKey(Academia, on_delete=models.CASCADE, related_name='modalidades')
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('academia', 'nome')
        verbose_name = "Modalidade"
        verbose_name_plural = "Modalidades"

    def __str__(self):
        return self.nome

# -----------------------------------------------------------------------------
# MODELOS DE ESTRUTURA DE AULAS
# -----------------------------------------------------------------------------

class Turma(models.Model):
    """ Representa uma turma, unindo modalidade, professor e alunos. """
    academia = models.ForeignKey(Academia, on_delete=models.CASCADE, related_name='turmas')
    modalidade = models.ForeignKey(Modalidade, on_delete=models.PROTECT, related_name='turmas')
    professor = models.ForeignKey(Professor, on_delete=models.SET_NULL, null=True, blank=True, related_name='turmas')
    alunos = models.ManyToManyField(Aluno, related_name='turmas', blank=True)
    limite_alunos = models.PositiveIntegerField(null=True, blank=True, help_text="Deixe em branco para ilimitado")
    ativa = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Turma"
        verbose_name_plural = "Turmas"

    def __str__(self):
        return f"{self.modalidade.nome} ({self.professor.nome_completo or 'A definir'})"

class Horario(models.Model):
    """ Representa um horário específico de uma turma. """
    turma = models.ForeignKey(Turma, on_delete=models.CASCADE, related_name='horarios')
    dias_semana = models.CharField(max_length=50, help_text="Ex: Seg, Ter, Qua")
    horario_inicio = models.TimeField()
    horario_fim = models.TimeField()

    class Meta:
        verbose_name = "Horário"
        verbose_name_plural = "Horários"

    def __str__(self):
        return f"{self.dias_semana} ({self.horario_inicio:%H:%M} - {self.horario_fim:%H:%M})"

# -----------------------------------------------------------------------------
# MODELOS FINANCEIROS (ESTRUTURA DE ASSINATURAS)
# -----------------------------------------------------------------------------

class Plano(models.Model):
    """ Representa um plano de pagamento oferecido pela academia. """
    academia = models.ForeignKey(Academia, on_delete=models.CASCADE, related_name='planos')
    nome = models.CharField(max_length=100)
    valor = models.DecimalField(max_digits=8, decimal_places=2)
    duracao_meses = models.PositiveIntegerField(default=1, help_text="Duração do plano em meses. 1 para mensal, 3 para trimestral, etc.")
    descricao = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.nome} (R$ {self.valor})"

class Assinatura(models.Model):
    """ Representa o 'contrato' de um aluno com um plano específico. """
    STATUS_CHOICES = [
        ('ativa', 'Ativa'),
        ('trancada', 'Trancada'),
        ('cancelada', 'Cancelada'),
    ]
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name='assinaturas')
    plano = models.ForeignKey(Plano, on_delete=models.PROTECT, related_name='assinaturas')
    academia = models.ForeignKey(Academia, on_delete=models.CASCADE, related_name='assinaturas')
    data_inicio = models.DateField(default=timezone.now)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ativa')

    def __str__(self):
        return f"Assinatura de {self.aluno.nome_completo} - Plano: {self.plano.nome}"

class Fatura(models.Model):
    """ Representa uma fatura (cobrança) gerada a partir de uma assinatura. """
    assinatura = models.ForeignKey(Assinatura, on_delete=models.CASCADE, related_name='faturas')
    academia = models.ForeignKey(Academia, on_delete=models.CASCADE, related_name='faturas')
    valor = models.DecimalField(max_digits=8, decimal_places=2)
    data_vencimento = models.DateField()
    data_pagamento = models.DateField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Fatura"
        verbose_name_plural = "Faturas"
        ordering = ['-data_vencimento']

    def __str__(self):
        return f"Fatura de {self.assinatura.aluno.nome_completo} - Venc: {self.data_vencimento.strftime('%d/%m/%Y')}"

    @property
    def status(self):
        if self.data_pagamento:
            return "Paga"
        if date.today() > self.data_vencimento:
            return "Vencida"
        return "Pendente"

# -----------------------------------------------------------------------------
# MODELOS DE REGISTRO DE ATIVIDADES
# -----------------------------------------------------------------------------

class Presenca(models.Model):
    """ Registra a presença de um aluno em uma data específica. """
    academia = models.ForeignKey(Academia, on_delete=models.CASCADE, related_name='presencas')
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name='presencas')
    turma = models.ForeignKey(Turma, on_delete=models.CASCADE, related_name='presencas', null=True, blank=True)
    data = models.DateField(default=timezone.now)

    class Meta:
        unique_together = ('aluno', 'data')
        verbose_name = "Presença"
        verbose_name_plural = "Presenças"

    def __str__(self):
        return f"Presença de {self.aluno.nome_completo} em {self.data.strftime('%d/%m/%Y')}"

class DiaNaoLetivo(models.Model):
    """ Registra um dia específico em que não haverá aulas na academia. """
    academia = models.ForeignKey(Academia, on_delete=models.CASCADE, related_name='dias_nao_letivos')
    data = models.DateField()
    descricao = models.CharField(max_length=200, help_text="Ex: Feriado de Ano Novo")

    class Meta:
        unique_together = ('academia', 'data')
        verbose_name = "Dia Não Letivo"
        verbose_name_plural = "Dias Não Letivos"
        ordering = ['data']

    def __str__(self):
        return f"{self.data.strftime('%d/%m/%Y')} - {self.descricao}"

# -----------------------------------------------------------------------------
# MODELOS DO SISTEMA DE GRADUAÇÃO
# -----------------------------------------------------------------------------

class Graduacao(models.Model):
    """
    Representa um nível de graduação (faixa, prajied, etc.) dentro de uma modalidade.
    """
    modalidade = models.ForeignKey(Modalidade, on_delete=models.CASCADE, related_name='graduacoes')
    academia = models.ForeignKey(Academia, on_delete=models.CASCADE, related_name='graduacoes')
    
    # Campo para um ícone visual (usando a classe do Bootstrap Icons)
    icone_arquivo = models.CharField(max_length=100, blank=True, null=True, help_text="Nome do arquivo do ícone (ex: faixa-azul.png)")
    
    nome = models.CharField(max_length=100, help_text="Ex: Faixa Branca, Prajied Vermelho e Branco")
    ordem = models.PositiveIntegerField(help_text="Ordem da graduação na hierarquia (1, 2, 3...)")

    # Novo campo para o tempo mínimo na graduação
    tempo_minimo_meses = models.PositiveIntegerField(default=6, help_text="Tempo mínimo em meses que o aluno deve permanecer nesta graduação.")

    # Novo campo para pré-requisitos textuais
    pre_requisitos = models.TextField(blank=True, null=True, help_text="Descreva os pré-requisitos (ex: Frequência mínima de 75%, técnicas X e Y).")

    class Meta:
        verbose_name = "Graduação"
        verbose_name_plural = "Graduações"
        unique_together = ('modalidade', 'ordem')
        ordering = ['modalidade', 'ordem']

    def __str__(self):
        return f"{self.modalidade.nome} - {self.nome} ({self.ordem}º)"

class HistoricoGraduacao(models.Model):
    """
    Registra a promoção de um aluno para uma nova graduação.
    """
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name='historico_graduacoes')
    graduacao = models.ForeignKey(Graduacao, on_delete=models.PROTECT, related_name='+') # O '+' impede a criação de uma relação reversa
    data_promocao = models.DateField(default=timezone.now)
    observacoes = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Histórico de Graduação"
        verbose_name_plural = "Históricos de Graduações"
        ordering = ['-data_promocao']

    def __str__(self):
        return f"{self.aluno.nome_completo} -> {self.graduacao.nome} em {self.data_promocao.strftime('%d/%m/%Y')}"


    @property
    def graduacao_atual(self):
        """ Retorna a graduação mais recente do aluno com base no histórico. """
        historico_recente = self.historico_graduacoes.order_by('-data_promocao').first()
        if historico_recente:
            return historico_recente.graduacao
        return None

class ExameGraduacao(models.Model):
    """ Representa um evento de exame de graduação agendado. """
    academia = models.ForeignKey(Academia, on_delete=models.CASCADE, related_name='exames')
    modalidade = models.ForeignKey(Modalidade, on_delete=models.CASCADE, related_name='exames')
    data_exame = models.DateTimeField()
    local = models.CharField(max_length=200, blank=True, null=True)
    responsavel = models.ForeignKey(Professor, on_delete=models.SET_NULL, null=True, blank=True)
    # Relação com os alunos inscritos através do modelo InscricaoExame
    inscritos = models.ManyToManyField(Aluno, through='InscricaoExame', related_name='exames_inscritos')

    class Meta:
        verbose_name = "Exame de Graduação"
        verbose_name_plural = "Exames de Graduação"
        ordering = ['-data_exame']

    def __str__(self):
        return f"Exame de {self.modalidade.nome} em {self.data_exame.strftime('%d/%m/%Y %H:%M')}"

class InscricaoExame(models.Model):
    """ Modelo 'through' que conecta um Aluno a um Exame, guardando o status. """
    STATUS_CHOICES = [
        ('convidado', 'Convidado'),
        ('confirmado', 'Confirmado'),
        ('aprovado', 'Aprovado'),
        ('reprovado', 'Reprovado'),
    ]
    exame = models.ForeignKey(ExameGraduacao, on_delete=models.CASCADE)
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE)
    graduacao_pretendida = models.ForeignKey(Graduacao, on_delete=models.PROTECT)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='convidado')
    data_inscricao = models.DateTimeField(auto_now_add=True)
    observacoes = models.TextField(blank=True, null=True, help_text="Feedback do professor em caso de reprovação.")

    class Meta:
        unique_together = ('exame', 'aluno') # Um aluno só pode se inscrever uma vez no mesmo exame

    def __str__(self):
        return f"{self.aluno.nome_completo} - {self.exame}"

class LogMensagem(models.Model):
    """
    Registra cada mensagem enviada pelo sistema via WhatsApp.
    Funciona como um histórico de notificações.
    """
    TIPO_CHOICES = [
        ('boas_vindas', 'Boas-Vindas'),
        ('inadimplencia', 'Inadimplência'),
        ('baixa_frequencia', 'Baixa Frequência'),
        ('convite_exame', 'Convite para Exame'),
        ('aprovacao_exame', 'Aprovação em Exame'),
        ('reprovacao_exame', 'Reprovação em Exame'),
        ('outro', 'Outro'),
    ]
    
    academia = models.ForeignKey(Academia, on_delete=models.CASCADE, related_name='logs_mensagens')
    aluno = models.ForeignKey(Aluno, on_delete=models.SET_NULL, null=True, related_name='logs_mensagens')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='outro')
    mensagem = models.TextField()
    data_envio = models.DateTimeField(auto_now_add=True)
    sucesso = models.BooleanField(default=True) # Para registrar se o gateway confirmou o envio
    resposta_gateway = models.TextField(blank=True, null=True) # Para guardar a resposta do serviço Node.js

    class Meta:
        verbose_name = "Log de Mensagem"
        verbose_name_plural = "Logs de Mensagens"
        ordering = ['-data_envio']

    def __str__(self):
        return f"Mensagem para {self.aluno.nome_completo} em {self.data_envio.strftime('%d/%m/%Y %H:%M')}"