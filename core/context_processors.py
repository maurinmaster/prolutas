from datetime import date
from .models import Aluno, Presenca, LogMensagem


def stats_context(request):
    """
    Context processor para fornecer estatísticas globais para todos os templates.
    """
    if not request.user.is_authenticated:
        return {}
    
    try:
        academia = request.user.academia_dono
        
        # Cards essenciais
        total_alunos = Aluno.objects.filter(academia=academia, ativo=True).count()
        presencas_hoje = Presenca.objects.filter(academia=academia, data=date.today()).count()
        mensagens_hoje = LogMensagem.objects.filter(academia=academia, data_envio__date=date.today()).count()
        
        return {
            'total_alunos': total_alunos,
            'presencas_hoje': presencas_hoje,
            'mensagens_hoje': mensagens_hoje,
        }
        
    except Exception:
        # Se houver qualquer erro, retorna valores padrão
        return {
            'total_alunos': '—',
            'presencas_hoje': '—',
            'mensagens_hoje': '—',
        }
