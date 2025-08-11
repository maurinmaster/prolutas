# core/management/commands/gerar_faturas.py

from datetime import date, timedelta # Importação corrigida
from django.core.management.base import BaseCommand
from core.models import Assinatura, Fatura
from dateutil.relativedelta import relativedelta

class Command(BaseCommand):
    help = 'Gera novas faturas para assinaturas ativas cujo ciclo de cobrança chegou ao fim.'

    def handle(self, *args, **options):
        hoje = date.today() # Usamos 'date' diretamente
        self.stdout.write(self.style.SUCCESS(f"--- [ROBÔ DE FATURAS] Iniciando verificação em {hoje.strftime('%d/%m/%Y')} ---"))

        assinaturas_ativas = Assinatura.objects.filter(status='ativa')
        total_gerado = 0
        
        for assinatura in assinaturas_ativas:
            aluno = assinatura.aluno
            plano = assinatura.plano

            # 1. Busca a última fatura gerada para esta assinatura.
            ultima_fatura = Fatura.objects.filter(assinatura=assinatura).order_by('-data_vencimento').first()

            if not ultima_fatura:
                self.stdout.write(f"AVISO: Assinatura de '{aluno.nome_completo}' não tem fatura inicial. Pulando. (Gerar via cadastro)")
                continue

            # 2. Se a última fatura ainda não foi paga, não faz nada.
            if not ultima_fatura.data_pagamento:
                self.stdout.write(f"Assinatura de '{aluno.nome_completo}' tem pendência na fatura de {ultima_fatura.data_vencimento.strftime('%d/%m/%Y')}. Pulando.")
                continue

            # 3. Se a última fatura foi paga, calcula quando a próxima deveria vencer.
            # Usamos relativedelta para somar os meses do plano à data de vencimento anterior.
            proximo_vencimento = ultima_fatura.data_vencimento + relativedelta(months=plano.duracao_meses)

            # 4. Verifica se já é hora de gerar a fatura do próximo ciclo.
            # Só gera a fatura se já estivermos no mês/ano do próximo vencimento.
            if hoje.year < proximo_vencimento.year or (hoje.year == proximo_vencimento.year and hoje.month < proximo_vencimento.month):
                self.stdout.write(f"Assinatura de '{aluno.nome_completo}' - Próximo ciclo em {proximo_vencimento.strftime('%m/%Y')}. Ainda não é hora. Pulando.")
                continue

            # 5. Se passou por todas as verificações, gera a nova fatura.
            Fatura.objects.create(
                assinatura=assinatura,
                academia=aluno.academia,
                valor=plano.valor,
                data_vencimento=proximo_vencimento
            )
            total_gerado += 1
            self.stdout.write(self.style.SUCCESS(f"-> FATURA GERADA para '{aluno.nome_completo}', Venc: {proximo_vencimento.strftime('%d/%m/%Y')}"))

        self.stdout.write(self.style.SUCCESS(f"--- [ROBÔ DE FATURAS] Verificação concluída. Total de {total_gerado} novas faturas geradas. ---"))