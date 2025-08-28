from django.core.management.base import BaseCommand
from core.models import PlanoSaaS, ConfiguracaoSistema


class Command(BaseCommand):
    help = 'Cria planos SaaS iniciais e configuração do sistema'

    def handle(self, *args, **options):
        self.stdout.write('Criando configuração do sistema...')
        
        # Criar configuração do sistema
        config, created = ConfiguracaoSistema.objects.get_or_create(
            id=1,
            defaults={
                'dias_trial_padrao': 30,
                'permitir_cadastro_publico': True,
                'email_suporte': 'suporte@prolutas.com',
                'sistema_em_manutencao': False,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('✓ Configuração do sistema criada'))
        else:
            self.stdout.write('✓ Configuração do sistema já existe')

        self.stdout.write('Criando planos SaaS...')
        
        # Plano Básico
        plano_basico, created = PlanoSaaS.objects.get_or_create(
            slug='basico',
            defaults={
                'nome': 'Básico',
                'descricao': 'Ideal para academias pequenas que estão começando',
                'preco_mensal': 49.90,
                'preco_anual': 499.00,
                'destaque': False,
                'ordem': 1,
                'max_alunos': 50,
                'max_professores': 3,
                'max_modalidades': 2,
                'max_turmas': 10,
                'integracao_whatsapp': True,
                'sistema_graduacao': True,
                'relatorios_avancados': False,
                'backup_automatico': False,
                'suporte_prioritario': False,
                'api_acesso': False,
                'ativo': True,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('✓ Plano Básico criado'))
        else:
            self.stdout.write('✓ Plano Básico já existe')

        # Plano Profissional
        plano_profissional, created = PlanoSaaS.objects.get_or_create(
            slug='profissional',
            defaults={
                'nome': 'Profissional',
                'descricao': 'Para academias em crescimento com mais recursos',
                'preco_mensal': 99.90,
                'preco_anual': 999.00,
                'destaque': True,
                'ordem': 2,
                'max_alunos': 200,
                'max_professores': 10,
                'max_modalidades': 5,
                'max_turmas': 50,
                'integracao_whatsapp': True,
                'sistema_graduacao': True,
                'relatorios_avancados': True,
                'backup_automatico': True,
                'suporte_prioritario': False,
                'api_acesso': False,
                'ativo': True,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('✓ Plano Profissional criado'))
        else:
            self.stdout.write('✓ Plano Profissional já existe')

        # Plano Enterprise
        plano_enterprise, created = PlanoSaaS.objects.get_or_create(
            slug='enterprise',
            defaults={
                'nome': 'Enterprise',
                'descricao': 'Solução completa para grandes academias e redes',
                'preco_mensal': 199.90,
                'preco_anual': 1999.00,
                'destaque': False,
                'ordem': 3,
                'max_alunos': 1000,
                'max_professores': 50,
                'max_modalidades': 20,
                'max_turmas': 200,
                'integracao_whatsapp': True,
                'sistema_graduacao': True,
                'relatorios_avancados': True,
                'backup_automatico': True,
                'suporte_prioritario': True,
                'api_acesso': True,
                'ativo': True,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('✓ Plano Enterprise criado'))
        else:
            self.stdout.write('✓ Plano Enterprise já existe')

        self.stdout.write(self.style.SUCCESS('\n🎉 Planos SaaS configurados com sucesso!'))
        self.stdout.write('\n📋 Planos disponíveis:')
        self.stdout.write(f'   • Básico: R$ {plano_basico.preco_mensal}/mês - até {plano_basico.max_alunos} alunos')
        self.stdout.write(f'   • Profissional: R$ {plano_profissional.preco_mensal}/mês - até {plano_profissional.max_alunos} alunos')
        self.stdout.write(f'   • Enterprise: R$ {plano_enterprise.preco_mensal}/mês - até {plano_enterprise.max_alunos} alunos')
        self.stdout.write('\n💡 Próximos passos:')
        self.stdout.write('   1. Configure suas chaves do Stripe no arquivo .env')
        self.stdout.write('   2. Acesse /admin/ para gerenciar os planos')
        self.stdout.write('   3. Teste o cadastro de academias em /planos/')