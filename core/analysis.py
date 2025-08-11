# core/analysis.py

import datetime
from django.db.models import Count, Sum, Max, Q
from langchain.tools import tool
from .models import Aluno, Plano, Fatura, Presenca, Academia, Assinatura, LogMensagem
import requests

# Funções de análise normais que nosso sistema usa
def analisar_frequencia(academia):
    """
    Coleta e analisa dados de frequência dos alunos da academia especificada.
    Retorna uma lista de alunos com baixa frequência.
    """
    data_limite = datetime.date.today() - datetime.timedelta(days=30)
    
    alunos_baixa_frequencia = Aluno.objects.filter(
        academia=academia,
        ativo=True,
        presencas__data__gte=data_limite
    ).annotate(
        num_presencas=Count('presencas')
    ).filter(
        num_presencas__lt=4 # Limite de baixa frequência (ex: menos de 4 presenças)
    ).order_by('num_presencas')
    
    return list(alunos_baixa_frequencia)

def analisar_financeiro(academia):
    """
    Coleta e analisa dados financeiros da academia especificada.
    Retorna um dicionário com os KPIs financeiros.
    """
    hoje = datetime.date.today()
    
    # --- INÍCIO DA NOVA LÓGICA ---
    # Faturamento do Mês Atual (pagamentos recebidos este mês)
    faturamento_mes_atual = Fatura.objects.filter(
        academia=academia,
        data_pagamento__year=hoje.year,
        data_pagamento__month=hoje.month
    ).aggregate(total=Sum('valor'))['total'] or 0
    # --- FIM DA NOVA LÓGICA ---

    # Cálculos que já tínhamos...
    primeiro_dia_mes_passado = (hoje.replace(day=1) - datetime.timedelta(days=1)).replace(day=1)
    ultimo_dia_mes_passado = hoje.replace(day=1) - datetime.timedelta(days=1)

    faturamento_mes_passado = Fatura.objects.filter(
        academia=academia,
        data_pagamento__range=(primeiro_dia_mes_passado, ultimo_dia_mes_passado)
    ).aggregate(total=Sum('valor'))['total'] or 0

    inadimplencia_total = Fatura.objects.filter(
        academia=academia,
        data_pagamento__isnull=True,
        data_vencimento__lt=hoje
    ).aggregate(total=Sum('valor'))['total'] or 0
    
    novas_assinaturas = Assinatura.objects.filter(
        academia=academia,
        data_inicio__range=(primeiro_dia_mes_passado, ultimo_dia_mes_passado)
    ).count()

    # Adicionamos a nova métrica ao dicionário de retorno
    return {
        "faturamento_mes_atual": faturamento_mes_atual, # Novo
        "periodo_mes_passado": f"{primeiro_dia_mes_passado.strftime('%d/%m')} a {ultimo_dia_mes_passado.strftime('%d/%m')}",
        "faturamento_mes_passado": faturamento_mes_passado,
        "inadimplencia": inadimplencia_total,
        "novas_assinaturas": novas_assinaturas
    }
def get_contagem_status_alunos(academia: Academia):
    """ Retorna a contagem de alunos ativos e inativos. """
    ativos = Aluno.objects.filter(academia=academia, ativo=True).count()
    inativos = Aluno.objects.filter(academia=academia, ativo=False).count()
    return {"ativos": ativos, "inativos": inativos}

def get_contagem_alunos_sem_assinatura(academia: Academia):
    """ Retorna a contagem de alunos ativos que não possuem uma assinatura ativa. """
    return Aluno.objects.filter(
        academia=academia, ativo=True
    ).exclude(
        assinaturas__status='ativa'
    ).count()

def get_alunos_ausentes_recentemente(academia: Academia, dias: int = 3):
    """ Retorna os nomes dos alunos que não têm presença nos últimos X dias. """
    data_limite = datetime.date.today() - datetime.timedelta(days=dias)
    
    # Anota a data da última presença de cada aluno ativo
    alunos_com_ultima_presenca = Aluno.objects.filter(academia=academia, ativo=True).annotate(
        ultima_presenca=Max('presencas__data')
    )
    
    # Filtra aqueles cuja última presença foi antes da data limite OU que nunca tiveram presença (ultima_presenca is None)
    alunos_ausentes = alunos_com_ultima_presenca.filter(
        Q(ultima_presenca__lt=data_limite) | Q(ultima_presenca__isnull=True)
    )
    
    return list(alunos_ausentes.values_list('nome_completo', flat=True))


@tool
def get_alunos_inadimplentes(academia_id: int):
    """Retorna uma lista com os nomes de todos os alunos com faturas vencidas e não pagas."""
    from .models import Academia
    try:
        academia = Academia.objects.get(id=academia_id)
    except Academia.DoesNotExist:
        return "Erro: Academia não encontrada."
    
    hoje = datetime.date.today()
    alunos = Aluno.objects.filter(
        academia=academia, ativo=True,
        assinaturas__faturas__data_pagamento__isnull=True,
        assinaturas__faturas__data_vencimento__lt=hoje
    ).distinct().values_list('nome_completo', flat=True)
    return list(alunos)


@tool
def get_detalhes_aluno(nome_aluno: str, academia_id: int):
    """Busca e retorna detalhes de um único aluno, como plano e contato."""
    from .models import Academia
    try:
        academia = Academia.objects.get(id=academia_id)
    except Academia.DoesNotExist:
        return "Erro: Academia não encontrada."

    try:
        aluno = Aluno.objects.get(academia=academia, nome_completo__icontains=nome_aluno)
        assinatura_ativa = aluno.assinaturas.filter(status='ativa').first()
        
        detalhes = {
            "nome": aluno.nome_completo, "contato": aluno.contato,
            "status": "Ativo" if aluno.ativo else "Inativo",
            "plano_ativo": assinatura_ativa.plano.nome if assinatura_ativa else "Nenhum",
            "dia_vencimento": aluno.dia_vencimento,
        }
        return detalhes
    except Aluno.DoesNotExist:
        return {"erro": "Aluno não encontrado."}
    except Aluno.MultipleObjectsReturned:
        return {"erro": "Múltiplos alunos encontrados. Por favor, seja mais específico."}

@tool
def get_contagem_total_alunos(academia_id: int):
    """
    Retorna o número total de alunos ATIVOS cadastrados na academia.
    """
    from .models import Academia
    try:
        academia = Academia.objects.get(id=academia_id)
    except Academia.DoesNotExist:
        return 0
    return Aluno.objects.filter(academia=academia, ativo=True).count()

@tool
def get_planos_cadastrados(academia_id: int):
    """
    Retorna uma lista com os nomes e valores de todos os planos cadastrados na academia.
    """
    from .models import Academia
    try:
        academia = Academia.objects.get(id=academia_id)
    except Academia.DoesNotExist:
        return []
    planos = Plano.objects.filter(academia=academia)
    return [{"nome": plano.nome, "valor": f"R$ {plano.valor}"} for plano in planos]

@tool
def get_nivel_inadimplencia(academia_id: int):
    """
    Calcula e retorna o valor total de todas as faturas vencidas e não pagas.
    """
    from .models import Academia
    try:
        academia = Academia.objects.get(id=academia_id)
    except Academia.DoesNotExist:
        return "Erro: Academia não encontrada."
    hoje = datetime.date.today()
    total_vencido = Fatura.objects.filter(
        academia=academia,
        data_pagamento__isnull=True,
        data_vencimento__lt=hoje
    ).aggregate(total=Sum('valor'))['total'] or 0
    return f"O valor total de faturas vencidas e não pagas é de R$ {total_vencido:.2f}."

@tool
def get_aluno_mais_faltoso(academia_id: int):
    """
    Identifica e retorna o nome do aluno ativo com o menor número de presenças nos últimos 30 dias.
    """
    from .models import Academia
    try:
        academia = Academia.objects.get(id=academia_id)
    except Academia.DoesNotExist:
        return "Erro: Academia não encontrada."
    data_limite = datetime.date.today() - datetime.timedelta(days=30)
    
    # Primeiro, pega todos os alunos ativos
    alunos_ativos = Aluno.objects.filter(academia=academia, ativo=True)
    if not alunos_ativos:
        return "Nenhum aluno ativo encontrado."

    # Anota o número de presenças recentes para cada um
    alunos_com_presencas = alunos_ativos.annotate(
        presencas_recentes=Count('presencas', filter=Q(presencas__data__gte=data_limite))
    ).order_by('presencas_recentes') # Ordena pelo menor número de presenças

    aluno_mais_faltoso = alunos_com_presencas.first()
    
    if aluno_mais_faltoso:
        return f"O aluno com menos presenças nos últimos 30 dias é {aluno_mais_faltoso.nome_completo}, com {aluno_mais_faltoso.presencas_recentes} check-ins."
    return "Não foi possível determinar o aluno mais faltoso."


@tool
def get_historico_pagamentos_aluno(academia_id: int, nome_aluno: str):
    """
    Busca e retorna o histórico de todas as faturas de um aluno específico, informando o status de cada uma.
    """
    from .models import Academia
    try:
        academia = Academia.objects.get(id=academia_id)
    except Academia.DoesNotExist:
        return {"erro": "Academia não encontrada."}
    try:
        aluno = Aluno.objects.get(academia=academia, nome_completo__icontains=nome_aluno)
        faturas = Fatura.objects.filter(assinatura__aluno=aluno).order_by('-data_vencimento')
        if not faturas.exists():
            return f"Nenhum histórico de faturas encontrado para {aluno.nome_completo}."

        historico = []
        for fatura in faturas:
            historico.append(
                f"Fatura de R$ {fatura.valor}, venc. {fatura.data_vencimento.strftime('%d/%m/%Y')}, Status: {fatura.status}"
            )
        return "\n".join(historico)
    except Aluno.DoesNotExist:
        return {"erro": "Aluno não encontrado."}
    except Aluno.MultipleObjectsReturned:
        return {"erro": "Múltiplos alunos encontrados com esse nome. Por favor, seja mais específico."}

def enviar_mensagem_whatsapp(academia, aluno, mensagem, tipo='outro'):
    """
    Envia uma requisição para o gateway Node.js E CRIA UM LOG da mensagem.
    """
    from django.conf import settings
    gateway_url = settings.WHATSAPP_GATEWAY_URL
    
    # Cria o log inicial. Vamos salvar a resposta do gateway depois.
    log = LogMensagem.objects.create(
        academia=academia,
        aluno=aluno,
        tipo=tipo,
        mensagem=mensagem
    )

    if not gateway_url:
        log.sucesso = False
        log.resposta_gateway = "URL do Gateway não configurada."
        log.save()
        return {"success": False, "error": "URL do Gateway não configurada."}

    headers = {'Content-Type': 'application/json'}
    payload = { "academiaId": str(academia.id), "number": aluno.contato, "message": mensagem }

    try:
        response = requests.post(f"{gateway_url}/send-message", json=payload, timeout=20)
        response.raise_for_status()
        
        resposta_json = response.json()
        log.resposta_gateway = str(resposta_json)
        log.sucesso = resposta_json.get('success', False)
        log.save()
        
        return resposta_json
    except requests.exceptions.RequestException as e:
        log.sucesso = False
        log.resposta_gateway = str(e)
        log.save()
        return {"success": False, "error": str(e)}
