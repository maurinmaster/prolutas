from django.apps import AppConfig
import os # Importe o módulo 'os'

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        # O Django define a variável de ambiente RUN_MAIN como 'true'
        # apenas no processo que roda a aplicação.
        if os.environ.get('RUN_MAIN'):
            from . import scheduler
            scheduler.start()