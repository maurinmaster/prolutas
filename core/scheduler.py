# core/scheduler.py

from apscheduler.schedulers.background import BackgroundScheduler
from django.core.management import call_command
from django_apscheduler.jobstores import DjangoJobStore
import sys
from core.models import Academia

def job_gerar_faturas():
    """
    Função que executa o comando para gerar faturas.
    """
    try:
        call_command('gerar_faturas')
        print("Tarefa 'gerar_faturas' executada com sucesso.")
    except Exception as e:
        print(f"Erro ao executar o job 'gerar_faturas': {e}")

def job_agente_ia():
    """
    Função que executa o nosso agente de IA para TODAS as academias cadastradas.
    """
    academias = Academia.objects.all()
    if not academias:
        print("Nenhuma academia encontrada para executar o agente de IA.")
        return
    
    for academia in academias:
        try:
            print(f"Executando agente de IA para a academia ID: {academia.id} ({academia.nome_fantasia})")
            call_command('agente_ia', academia.id)
        except Exception as e:
            print(f"Erro ao executar o job 'agente_ia' para a academia ID {academia.id}: {e}")

def start():
    """
    Inicia o agendador e define todas as tarefas a serem executadas.
    """
    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), "default")
    
    # Tarefa 1: Gerar faturas (todos os dias às 03:00 da manhã)
    scheduler.add_job(
        job_gerar_faturas,
        trigger='cron',
        hour='3',
        minute='00',
        id='job_gerar_faturas_diario',
        replace_existing=True,
    )
    print("-> Tarefa 'gerar_faturas' agendada para 03:00.")
    
    # --- NOVA TAREFA ---
    # Tarefa 2: Rodar o Agente de IA (todos os dias às 08:00 da manhã)
    scheduler.add_job(
        job_agente_ia,
        trigger='cron',
        hour='10', # Podemos escolher um horário diferente, como 8 da manhã
        minute='00',
        id='job_agente_ia_diario', # ID único para o novo job
        replace_existing=True,
    )
    print("-> Tarefa 'agente_ia' agendada para 10:00.")
    
    print("\nAgendador de tarefas iniciado...")
    scheduler.start()