# core/management/commands/agente_ia.py

import datetime
import os
from django.core.management.base import BaseCommand
from django.db.models import Q

# Importações do LangChain
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage

# Importações dos nossos módulos e modelos
from core import analysis
from core.analysis import enviar_mensagem_whatsapp
from core.models import Academia, Aluno, Fatura, Assinatura


class Command(BaseCommand):
    help = 'Executa o agente de IA para uma análise completa da academia, envia notificações e gera um relatório.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("--- 🤖 Agente Assistente iniciando varredura... ---"))
        
        academia = Academia.objects.first()
        if not academia:
            self.stdout.write(self.style.ERROR("Nenhuma academia encontrada para analisar."))
            return

        self.stdout.write(f"Analisando dados para a academia: {academia.nome_fantasia}")

        # --- FASE 1: COLETA DE DADOS ---
        # Chamada correta para a ferramenta LangChain
        inadimplentes_nomes = analysis.get_alunos_inadimplentes.invoke({"academia_id": academia.id})
        alunos_faltosos = analysis.analisar_frequencia(academia)
        
        data_limite_novos = datetime.date.today() - datetime.timedelta(days=7)
        novos_alunos = Aluno.objects.filter(academia=academia, data_matricula__gte=data_limite_novos)

        # --- FASE 2: EXECUÇÃO DE NOTIFICAÇÕES (LÓGICA COMPLETA) ---
        
        self.stdout.write(self.style.WARNING("\nIniciando ciclo de notificações..."))
        
        # 2.1 Notificação de Inadimplência
        if academia.notificar_inadimplencia and inadimplentes_nomes:
            self.stdout.write("-> Verificando inadimplentes...")
            for nome in inadimplentes_nomes:
                try:
                    aluno_obj = Aluno.objects.get(academia=academia, nome_completo__icontains=nome)
                    # VERIFICAÇÃO DE PERMISSÃO
                    if aluno_obj.contato and aluno_obj.receber_notificacoes:
                        mensagem = f"Olá {aluno_obj.nome_completo.split()[0]}! Passando para lembrar que sua mensalidade na {academia.nome_fantasia} está em aberto. Se precisar de ajuda, é só chamar! 😊"
                        enviar_mensagem_whatsapp(academia, aluno_obj.contato, mensagem, tipo='inadimplencia')
                        self.stdout.write(self.style.SUCCESS(f"   - Ordem de envio de cobrança para {aluno_obj.nome_completo}"))
                    elif not aluno_obj.receber_notificacoes:
                        self.stdout.write(f"   - Aluno {aluno_obj.nome_completo} optou por não receber notificações. Pulando.")
                except (Aluno.DoesNotExist, Aluno.MultipleObjectsReturned):
                    continue

        # 2.2 Notificação de Faltas
        if academia.notificar_faltas and alunos_faltosos:
            self.stdout.write("-> Verificando alunos com baixa frequência...")
            for aluno in alunos_faltosos:
                # VERIFICAÇÃO DE PERMISSÃO
                if aluno.contato and aluno.receber_notificacoes:
                    mensagem = f"Olá {aluno.nome_completo.split()[0]}, tudo bem? Sentimos sua falta nos treinos da {academia.nome_fantasia}! 💪 Esperamos te ver em breve!"
                    enviar_mensagem_whatsapp(academia, aluno.contato, mensagem, tipo='baixa_frequencia')
                    self.stdout.write(self.style.SUCCESS(f"   - Ordem de envio de ausência para {aluno.nome_completo}"))
                elif not aluno.receber_notificacoes:
                    self.stdout.write(f"   - Aluno {aluno.nome_completo} optou por não receber notificações. Pulando.")

        # 2.3 Notificação de Boas-Vindas
        if academia.notificar_boas_vindas and novos_alunos.exists():
            self.stdout.write("-> Verificando novos alunos...")
            for aluno in novos_alunos:
                # VERIFICAÇÃO DE PERMISSÃO
                if aluno.contato and aluno.receber_notificacoes:
                    mensagem = f"Seja muito bem-vindo(a) à {academia.nome_fantasia}, {aluno.nome_completo.split()[0]}! 🎉 Estamos muito felizes em ter você no nosso time. Bons treinos!"
                    enviar_mensagem_whatsapp(academia, aluno.contato, mensagem, tipo='boas_vindas')
                    self.stdout.write(self.style.SUCCESS(f"   - Ordem de envio de boas-vindas para {aluno.nome_completo}"))
                elif not aluno.receber_notificacoes:
                    self.stdout.write(f"   - Aluno {aluno.nome_completo} optou por não receber notificações. Pulando.")

        self.stdout.write("\n--- Fim do ciclo de notificações ---")
        
        # --- FASE 3: MONTAGEM E ENVIO PARA IA ---
        self.stdout.write("\nPreparando resumo para o assistente Gemini...")
        
        # Montagem do relatório bruto para a IA
        relatorio_bruto = "## Relatório de Status e Ações Sugeridas\n\n"
        relatorio_bruto += "### 1. Inadimplência\n"
        if inadimplentes_nomes:
            for nome in inadimplentes_nomes: 
                relatorio_bruto += f"- {nome}\n"
        else:
            relatorio_bruto += "Nenhum aluno inadimplente.\n"
        
        relatorio_bruto += "\n### 2. Alunos com Baixa Frequência\n"
        if alunos_faltosos:
            for aluno in alunos_faltosos:
                relatorio_bruto += f"- {aluno.nome_completo}\n"
        else:
            relatorio_bruto += "Nenhum aluno com baixa frequência.\n"
        
        relatorio_bruto += "\n### 3. Novos Alunos (últimos 7 dias)\n"
        if novos_alunos.exists():
            for aluno in novos_alunos:
                relatorio_bruto += f"- {aluno.nome_completo} (matriculado em {aluno.data_matricula.strftime('%d/%m/%Y')})\n"
        else:
            relatorio_bruto += "Nenhum novo aluno nos últimos 7 dias.\n"
        
        # Adiciona informações gerais da academia
        relatorio_bruto += f"\n### 4. Informações Gerais\n"
        relatorio_bruto += f"- Academia: {academia.nome_fantasia}\n"
        relatorio_bruto += f"- Data da análise: {datetime.date.today().strftime('%d/%m/%Y')}\n"
        
        try:
            # Configuração do modelo LangChain
            GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
            if not GEMINI_API_KEY:
                self.stdout.write(self.style.ERROR("GEMINI_API_KEY não configurada no ambiente."))
                return
            
            # Inicializa o modelo LangChain
            model = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=GEMINI_API_KEY,
                temperature=0.7
            )
            
            # Template do prompt para análise
            prompt_template = ChatPromptTemplate.from_template("""
            Você é um assistente especializado em gestão de academias de artes marciais.
            
            Analise o seguinte relatório e forneça:
            1. Um resumo executivo dos pontos principais
            2. Recomendações específicas para melhorar a gestão
            3. Alertas sobre situações que precisam de atenção imediata
            4. Sugestões de ações para reter alunos e melhorar a frequência
            
            Relatório:
            {relatorio}
            
            Responda de forma clara, objetiva e em português brasileiro.
            """)
            
            # Executa a análise
            chain = prompt_template | model
            response = chain.invoke({"relatorio": relatorio_bruto})
            
            # Exibe o resultado
            self.stdout.write(self.style.SUCCESS("\n--- 📊 ANÁLISE DO ASSISTENTE IA ---"))
            self.stdout.write(response.content)
            self.stdout.write(self.style.SUCCESS("--- Fim da análise ---"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Ocorreu um erro ao contatar a API do Gemini: {e}"))

        self.stdout.write(self.style.SUCCESS("--- ✅ Varredura do Agente concluída. ---"))