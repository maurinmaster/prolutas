from django.db import models
from django.contrib.auth.models import User
from core.models import PlanoSaaS, AssinaturaSaaS
from django.utils import timezone

# Create your models here.

class Lead(models.Model):
    """
    Representa um lead (potencial cliente) que visitou o site de vendas.
    """
    STATUS_CHOICES = [
        ('novo', 'Novo'),
        ('contatado', 'Contatado'),
        ('qualificado', 'Qualificado'),
        ('convertido', 'Convertido'),
        ('perdido', 'Perdido'),
    ]
    
    nome = models.CharField(max_length=100)
    email = models.EmailField()
    telefone = models.CharField(max_length=20, blank=True, null=True)
    empresa = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='novo')
    
    # Informações da visita
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_ultimo_contato = models.DateTimeField(null=True, blank=True)
    origem = models.CharField(max_length=50, default='site', help_text="Como o lead chegou ao site")
    
    # Interesse
    plano_interesse = models.ForeignKey(PlanoSaaS, on_delete=models.SET_NULL, null=True, blank=True)
    observacoes = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Lead"
        verbose_name_plural = "Leads"
        ordering = ['-data_criacao']
    
    def __str__(self):
        return f"{self.nome} ({self.email})"


class SessaoVenda(models.Model):
    """
    Registra sessões de vendas para análise de conversão.
    """
    session_id = models.CharField(max_length=100, unique=True)
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, null=True, blank=True)
    
    # Informações da sessão
    data_inicio = models.DateTimeField(auto_now_add=True)
    data_fim = models.DateTimeField(null=True, blank=True)
    duracao_segundos = models.PositiveIntegerField(null=True, blank=True)
    
    # Páginas visitadas
    pagina_inicial = models.CharField(max_length=200, blank=True, null=True)
    pagina_final = models.CharField(max_length=200, blank=True, null=True)
    
    # Conversão
    converteu = models.BooleanField(default=False)
    plano_escolhido = models.ForeignKey(PlanoSaaS, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = "Sessão de Venda"
        verbose_name_plural = "Sessões de Venda"
        ordering = ['-data_inicio']
    
    def __str__(self):
        return f"Sessão {self.session_id} - {self.data_inicio.strftime('%d/%m/%Y %H:%M')}"


class CupomDesconto(models.Model):
    """
    Cupons de desconto para promoções.
    """
    codigo = models.CharField(max_length=20, unique=True)
    descricao = models.CharField(max_length=200)
    desconto_percentual = models.DecimalField(max_digits=5, decimal_places=2, help_text="Desconto em porcentagem")
    desconto_fixo = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Desconto fixo em reais")
    
    # Validade
    data_inicio = models.DateTimeField()
    data_fim = models.DateTimeField()
    ativo = models.BooleanField(default=True)
    
    # Limites
    max_usos = models.PositiveIntegerField(null=True, blank=True, help_text="Número máximo de usos (deixe em branco para ilimitado)")
    usos_atuais = models.PositiveIntegerField(default=0)
    
    # Aplicação
    aplicavel_planos = models.ManyToManyField(PlanoSaaS, blank=True, help_text="Planos onde o cupom pode ser aplicado")
    desconto_minimo = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Valor mínimo da compra para aplicar o desconto")
    
    class Meta:
        verbose_name = "Cupom de Desconto"
        verbose_name_plural = "Cupons de Desconto"
        ordering = ['-data_inicio']
    
    def __str__(self):
        return f"{self.codigo} - {self.desconto_percentual}%"
    
    @property
    def esta_valido(self):
        """Verifica se o cupom está válido"""
        agora = timezone.now()
        return (
            self.ativo and
            self.data_inicio <= agora <= self.data_fim and
            (self.max_usos is None or self.usos_atuais < self.max_usos)
        )
    
    def aplicar_desconto(self, valor_original):
        """Aplica o desconto ao valor original"""
        if self.desconto_fixo > 0:
            return max(0, valor_original - self.desconto_fixo)
        else:
            return valor_original * (1 - self.desconto_percentual / 100)


class ConfiguracaoVendas(models.Model):
    """
    Configurações específicas do site de vendas.
    """
    titulo_site = models.CharField(max_length=100, default="Gestão de Lutas - SaaS")
    subtitulo_site = models.CharField(max_length=200, default="Sistema completo para gestão de academias de artes marciais")
    
    # Cores e branding
    cor_primaria = models.CharField(max_length=7, default="#007bff", help_text="Cor primária em hexadecimal")
    cor_secundaria = models.CharField(max_length=7, default="#6c757d", help_text="Cor secundária em hexadecimal")
    
    # Conteúdo
    texto_hero = models.TextField(help_text="Texto principal da página inicial")
    beneficios_destaque = models.TextField(help_text="Benefícios principais do sistema")
    
    # Contato
    email_contato = models.EmailField(blank=True, null=True)
    telefone_contato = models.CharField(max_length=20, blank=True, null=True)
    whatsapp_contato = models.CharField(max_length=20, blank=True, null=True)
    
    # Redes sociais
    facebook_url = models.URLField(blank=True, null=True)
    instagram_url = models.URLField(blank=True, null=True)
    linkedin_url = models.URLField(blank=True, null=True)
    
    # Configurações de conversão
    trial_dias = models.PositiveIntegerField(default=14, help_text="Dias de período de teste gratuito")
    mostrar_precos = models.BooleanField(default=True, help_text="Se deve mostrar os preços publicamente")
    
    class Meta:
        verbose_name = "Configuração de Vendas"
        verbose_name_plural = "Configurações de Vendas"
    
    def __str__(self):
        return "Configurações do Site de Vendas"
    
    @classmethod
    def get_config(cls):
        """Retorna a configuração atual ou cria uma nova"""
        config, created = cls.objects.get_or_create(pk=1)
        return config
