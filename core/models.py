from datetime import date
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from threading import local

# Thread-local storage para armazenar a academia atual
_thread_locals = local()

def get_current_academia():
    """Retorna a academia atual do contexto da thread"""
    return getattr(_thread_locals, 'academia', None)

def set_current_academia(academia):
    """Define a academia atual no contexto da thread"""
    _thread_locals.academia = academia

class TenantManager(models.Manager):
    """Manager que filtra automaticamente por academia"""
    
    def get_queryset(self):
        queryset = super().get_queryset()
        academia = get_current_academia()
        if academia and hasattr(self.model, 'academia'):
            return queryset.filter(academia=academia)
        return queryset
    
    def all_tenants(self):
        """Retorna todos os registros sem filtro de academia (para superadmin)"""
        return super().get_queryset()

class TenantModel(models.Model):
    """Classe base para modelos que devem ser filtrados por academia"""
    
    objects = TenantManager()
    all_objects = models.Manager()  # Manager sem filtro
    
    class Meta:
        abstract = True
    
    def save(self, *args, **kwargs):
        # Se não tem academia definida, usa a academia atual
        if hasattr(self, 'academia') and not self.academia_id:
            academia = get_current_academia()
            if academia:
                self.academia = academia
        super().save(*args, **kwargs)

# -----------------------------------------------------------------------------
# MODELOS PRINCIPAIS E CADASTROS AUXILIARES
# -----------------------------------------------------------------------------



class Academia(models.Model):
    """ Representa uma academia que utiliza o sistema (o 'inquilino' do SaaS). """
    nome_fantasia = models.CharField(max_length=100, help_text="Nome popular da academia")
    razao_social = models.CharField(max_length=100, help_text="Nome legal da empresa")
    slug = models.SlugField(max_length=100, unique=True, default='academia-temp', help_text="Identificador único da academia para URLs (ex: academia-santos)")
    cnpj = models.CharField(max_length=18, blank=True, null=True, unique=True, help_text="CNPJ da academia (formato XX.XXX.XXX/XXXX-XX) - Opcional para pessoas físicas")
    telefone = models.CharField(max_length=20, blank=True, null=True, help_text="Telefone de contato principal")
    endereco = models.CharField(max_length=255, blank=True, null=True, help_text="Endereço completo da academia")
    dono = models.OneToOneField(User, on_delete=models.PROTECT, related_name='academia_dono')
    data_cadastro = models.DateTimeField(auto_now_add=True)
    ativa = models.BooleanField(default=True, help_text="Se a academia está ativa no sistema")
    dominio_personalizado = models.CharField(max_length=100, blank=True, null=True, help_text="Domínio personalizado (ex: minhaacademia.com.br)")

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
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nome_fantasia)
            # Garante que o slug seja único
            original_slug = self.slug
            counter = 1
            while Academia.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)
    
    def clean(self):
        if self.slug and Academia.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
            raise ValidationError({'slug': 'Este slug já está em uso por outra academia.'})
    
    @property
    def url_base(self):
        """Retorna a URL base da academia para uso em templates"""
        return f"/{self.slug}/"

class Aluno(TenantModel):
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

class Professor(TenantModel):
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

class Modalidade(TenantModel):
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

class Turma(TenantModel):
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

class Plano(TenantModel):
    """ Representa um plano de pagamento oferecido pela academia. """
    academia = models.ForeignKey(Academia, on_delete=models.CASCADE, related_name='planos')
    nome = models.CharField(max_length=100)
    valor = models.DecimalField(max_digits=8, decimal_places=2)
    duracao_meses = models.PositiveIntegerField(default=1, help_text="Duração do plano em meses. 1 para mensal, 3 para trimestral, etc.")
    descricao = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.nome} (R$ {self.valor})"

class Assinatura(TenantModel):
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

class Fatura(TenantModel):
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

class Presenca(TenantModel):
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

class DiaNaoLetivo(TenantModel):
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

class Graduacao(TenantModel):
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

class HistoricoGraduacao(TenantModel):
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

class ExameGraduacao(TenantModel):
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

# -----------------------------------------------------------------------------
# MODELOS SAAS MULTI-TENANT
# -----------------------------------------------------------------------------

class ConfiguracaoSistema(models.Model):
    """Configurações globais do sistema SaaS"""
    dias_trial_padrao = models.PositiveIntegerField(default=30, help_text="Dias de trial padrão para novas academias")
    permitir_cadastro_publico = models.BooleanField(default=True, help_text="Permitir que academias se cadastrem publicamente")
    email_suporte = models.EmailField(default="suporte@prolutas.com", help_text="Email de suporte técnico")
    mensagem_manutencao = models.TextField(blank=True, null=True, help_text="Mensagem exibida durante manutenção")
    sistema_em_manutencao = models.BooleanField(default=False, help_text="Ativar modo de manutenção")
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Configuração do Sistema"
        verbose_name_plural = "Configurações do Sistema"
    
    def __str__(self):
        return "Configurações do Sistema"
    
    @classmethod
    def get_config(cls):
        """Retorna a configuração do sistema (singleton)"""
        config, created = cls.objects.get_or_create(pk=1)
        return config

class PlanoSaaS(models.Model):
    """Planos disponíveis para as academias no sistema SaaS"""
    nome = models.CharField(max_length=100, help_text="Nome do plano (ex: Básico, Profissional, Enterprise)")
    slug = models.SlugField(unique=True, help_text="Identificador único do plano para URLs")
    descricao = models.TextField(help_text="Descrição das funcionalidades do plano")
    preco_mensal = models.DecimalField(max_digits=10, decimal_places=2, help_text="Preço mensal em reais")
    preco_anual = models.DecimalField(max_digits=10, decimal_places=2, help_text="Preço anual em reais")
    destaque = models.BooleanField(default=False, help_text="Se este plano deve ser destacado na página de vendas")
    ordem = models.PositiveIntegerField(default=1, help_text="Ordem de exibição dos planos")
    
    # Limites do plano
    max_alunos = models.PositiveIntegerField(help_text="Número máximo de alunos permitidos")
    max_professores = models.PositiveIntegerField(help_text="Número máximo de professores permitidos")
    max_modalidades = models.PositiveIntegerField(help_text="Número máximo de modalidades permitidas")
    max_turmas = models.PositiveIntegerField(help_text="Número máximo de turmas permitidas")
    
    # Funcionalidades
    integracao_whatsapp = models.BooleanField(default=True, help_text="Permite integração com WhatsApp")
    sistema_graduacao = models.BooleanField(default=True, help_text="Permite sistema de graduação/faixas")
    relatorios_avancados = models.BooleanField(default=False, help_text="Acesso a relatórios avançados")
    backup_automatico = models.BooleanField(default=False, help_text="Backup automático dos dados")
    suporte_prioritario = models.BooleanField(default=False, help_text="Suporte técnico prioritário")
    api_acesso = models.BooleanField(default=False, help_text="Acesso à API para integrações")
    
    # Integração com gateway de pagamento
    stripe_price_id_mensal = models.CharField(max_length=100, blank=True, null=True, help_text="ID do preço mensal no Stripe")
    stripe_price_id_anual = models.CharField(max_length=100, blank=True, null=True, help_text="ID do preço anual no Stripe")
    stripe_product_id = models.CharField(max_length=100, blank=True, null=True, help_text="ID do produto no Stripe")
    
    ativo = models.BooleanField(default=True, help_text="Se o plano está disponível para novas assinaturas")
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Plano SaaS"
        verbose_name_plural = "Planos SaaS"
        ordering = ['ordem', 'nome']
    
    def __str__(self):
        return self.nome
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nome)
        super().save(*args, **kwargs)

class AssinaturaSaaS(models.Model):
    """Assinatura de uma academia a um plano SaaS"""
    STATUS_CHOICES = [
        ('trial', 'Período de Teste'),
        ('ativa', 'Ativa'),
        ('suspensa', 'Suspensa por Inadimplência'),
        ('cancelada', 'Cancelada'),
        ('expirada', 'Expirada'),
    ]
    
    CICLO_CHOICES = [
        ('mensal', 'Mensal'),
        ('anual', 'Anual'),
    ]
    
    academia = models.OneToOneField(Academia, on_delete=models.CASCADE, related_name='assinatura_saas')
    plano = models.ForeignKey(PlanoSaaS, on_delete=models.PROTECT, related_name='assinaturas')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='trial')
    ciclo_pagamento = models.CharField(max_length=10, choices=CICLO_CHOICES, default='mensal')
    
    # Datas importantes
    data_inicio = models.DateTimeField(default=timezone.now)
    data_fim_trial = models.DateTimeField(blank=True, null=True, help_text="Data de fim do período de teste")
    data_vencimento = models.DateField(blank=True, null=True, help_text="Data de vencimento da próxima cobrança")
    data_cancelamento = models.DateTimeField(blank=True, null=True)
    
    # Integração com gateway de pagamento
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True, help_text="ID do cliente no Stripe")
    stripe_subscription_id = models.CharField(max_length=100, blank=True, null=True, help_text="ID da assinatura no Stripe")
    
    # Valores e descontos
    valor_atual = models.DecimalField(max_digits=10, decimal_places=2, help_text="Valor atual da assinatura")
    desconto_percentual = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Desconto aplicado em percentual")
    desconto_fixo = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Desconto fixo aplicado")
    
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Assinatura SaaS"
        verbose_name_plural = "Assinaturas SaaS"
        ordering = ['-data_criacao']
    
    def __str__(self):
        return f"{self.academia.nome_fantasia} - {self.plano.nome} ({self.status})"
    
    @property
    def em_trial(self):
        """Verifica se a assinatura está em período de teste"""
        return self.status == 'trial' and self.data_fim_trial and timezone.now() < self.data_fim_trial
    
    @property
    def trial_expirado(self):
        """Verifica se o período de teste expirou"""
        return self.status == 'trial' and self.data_fim_trial and timezone.now() >= self.data_fim_trial
    
    def calcular_valor_com_desconto(self):
        """Calcula o valor final com descontos aplicados"""
        valor_base = self.plano.preco_mensal if self.ciclo_pagamento == 'mensal' else self.plano.preco_anual
        valor_com_desconto = valor_base - self.desconto_fixo
        if self.desconto_percentual > 0:
            valor_com_desconto = valor_com_desconto * (1 - self.desconto_percentual / 100)
        return max(valor_com_desconto, 0)  # Não permite valores negativos

class PagamentoSaaS(models.Model):
    """Registro de pagamentos das assinaturas SaaS"""
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('pago', 'Pago'),
        ('falhou', 'Falhou'),
        ('cancelado', 'Cancelado'),
        ('reembolsado', 'Reembolsado'),
    ]
    
    assinatura = models.ForeignKey(AssinaturaSaaS, on_delete=models.CASCADE, related_name='pagamentos')
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    data_vencimento = models.DateField()
    data_pagamento = models.DateTimeField(blank=True, null=True)
    
    # Integração com gateway de pagamento
    stripe_payment_intent_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_invoice_id = models.CharField(max_length=100, blank=True, null=True)
    
    descricao = models.TextField(blank=True, null=True)
    observacoes = models.TextField(blank=True, null=True)
    
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Pagamento SaaS"
        verbose_name_plural = "Pagamentos SaaS"
        ordering = ['-data_vencimento']
    
    def __str__(self):
        return f"{self.assinatura.academia.nome_fantasia} - R$ {self.valor} ({self.status})"

class HistoricoAssinaturaSaaS(models.Model):
    """Histórico de eventos das assinaturas SaaS"""
    TIPO_EVENTO_CHOICES = [
        ('criacao', 'Criação da Assinatura'),
        ('upgrade', 'Upgrade de Plano'),
        ('downgrade', 'Downgrade de Plano'),
        ('suspensao', 'Suspensão por Inadimplência'),
        ('reativacao', 'Reativação'),
        ('cancelamento', 'Cancelamento'),
        ('pagamento', 'Pagamento Recebido'),
        ('falha_pagamento', 'Falha no Pagamento'),
        ('inicio_trial', 'Início do Período de Teste'),
        ('fim_trial', 'Fim do Período de Teste'),
    ]
    
    assinatura = models.ForeignKey(AssinaturaSaaS, on_delete=models.CASCADE, related_name='historico')
    tipo_evento = models.CharField(max_length=20, choices=TIPO_EVENTO_CHOICES)
    descricao = models.TextField(help_text="Descrição detalhada do evento")
    
    # Para mudanças de plano
    plano_anterior = models.ForeignKey(PlanoSaaS, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    plano_atual = models.ForeignKey(PlanoSaaS, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    valor_anterior = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    valor_atual = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Integração com gateway de pagamento
    stripe_invoice_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_payment_intent_id = models.CharField(max_length=100, blank=True, null=True)
    
    usuario_responsavel = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, help_text="Usuário que executou a ação (se aplicável)")
    data_evento = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Histórico de Assinatura SaaS"
        verbose_name_plural = "Históricos de Assinaturas SaaS"
        ordering = ['-data_evento']
    
    def __str__(self):
        return f"{self.assinatura.academia.nome_fantasia} - {self.get_tipo_evento_display()} ({self.data_evento.strftime('%d/%m/%Y %H:%M')})"

class LogMensagem(TenantModel):
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



