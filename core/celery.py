import os
from celery import Celery

# Define o módulo de configurações padrão do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Cria a instância do Celery
app = Celery('prolutas')

# Usa as configurações do Django
app.config_from_object('django.conf:settings', namespace='CELERY')

# Carrega tarefas automaticamente de todos os apps registrados
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
