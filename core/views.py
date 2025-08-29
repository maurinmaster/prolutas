from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction, models
from django.db.models.deletion import ProtectedError
from django.forms import inlineformset_factory
from datetime import date, timedelta, datetime
import os
from django.contrib import messages
from django.db.models import Count, Q, Sum
from dateutil.relativedelta import relativedelta
from django.core.paginator import Paginator
import calendar

# core/views.py (no topo, com os outros imports)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import PerguntaIASerializer
from core.analysis import enviar_mensagem_whatsapp

#funções langchain
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage

from . import analysis

from .models import (
    Academia, Aluno, Turma, Horario, Modalidade, Professor, Presenca, DiaNaoLetivo,
    Plano, Assinatura, Fatura, Graduacao, ExameGraduacao, HistoricoGraduacao, InscricaoExame, LogMensagem
)
from .forms import (
    CustomUserCreationForm, AcademiaForm, AlunoForm, TurmaForm, HorarioForm,
    ModalidadeForm, ProfessorForm, DiaNaoLetivoForm, PlanoForm, AssinaturaForm,
    RegistrarPagamentoForm, AlterarVencimentoForm, ConfiguracaoWhatsAppForm, GraduacaoForm, ExameGraduacaoForm, HistoricoGraduacaoForm,
    ReprovacaoForm
)

# -----------------------------------------------------------------------------
# CADASTRO E PÁGINAS PRINCIPAIS
# -----------------------------------------------------------------------------

def pagina_inicial(request, slug=None):
    """View para a página inicial"""
    if request.user.is_authenticated:
        if slug:
            return redirect('dashboard', slug=slug)
        else:
            # Se não há slug, redireciona para login_redirect que vai determinar a academia
            return redirect('login_redirect')
    else:
        # Redireciona para o login
        return redirect('login')

@transaction.atomic
def cadastro_academia(request, slug=None):
    if request.user.is_authenticated:
        if slug:
            return redirect('dashboard', slug=slug)
        else:
            return redirect('login_redirect')
    
    if request.method == 'POST':
        form_user = CustomUserCreationForm(request.POST)
        form_academia = AcademiaForm(request.POST)
        if form_user.is_valid() and form_academia.is_valid():
            user = form_user.save()
            academia = form_academia.save(commit=False)
            academia.dono = user
            academia.save()
            return redirect('login') # Redireciona para o login após o sucesso
    else:
        form_user = CustomUserCreationForm()
        form_academia = AcademiaForm()

    return render(request, 'core/cadastro.html', {
        'form_user': form_user,
        'form_academia': form_academia
    })

# -----------------------------------------------------------------------------
# CRUD DE ALUNOS
# -----------------------------------------------------------------------------

@login_required
def aluno_add(request, slug=None):
    if request.method == 'POST':
        form = AlunoForm(request.POST, request.FILES)
        if form.is_valid():
            aluno = form.save(commit=False)
            # A academia é obtida automaticamente do middleware
            aluno.academia = request.academia
            aluno.save()
            return redirect('dashboard', slug=request.academia.slug)
    else:
        form = AlunoForm()
    return render(request, 'core/aluno_form.html', {'form': form, 'tipo': 'Adicionar'})


@login_required
def aluno_edit(request, pk):
    # O filtro por academia é automático através do TenantManager
    aluno = get_object_or_404(Aluno, pk=pk)
    if request.method == 'POST':
        form = AlunoForm(request.POST, request.FILES, instance=aluno)
        if form.is_valid():
            form.save()
            return redirect('dashboard', slug=aluno.academia.slug)
    else:
        form = AlunoForm(instance=aluno) # Argumento 'academia' removido daqui.
    return render(request, 'core/aluno_form.html', {'form': form, 'tipo': 'Editar'})

@login_required
def aluno_delete(request, pk):
    aluno = get_object_or_404(Aluno, pk=pk, academia=request.academia)
    if request.method == 'POST':
        aluno.delete()
    return redirect('dashboard', slug=aluno.academia.slug)

# -----------------------------------------------------------------------------
# CRUD DE TURMAS (COM FORMSETS)
# -----------------------------------------------------------------------------

@login_required
def turma_add(request, slug=None):
    academia = request.academia
    HorarioFormSet = inlineformset_factory(Turma, Horario, form=HorarioForm, extra=1, can_delete=False)
    if request.method == 'POST':
        form = TurmaForm(request.POST, academia=academia)
        formset = HorarioFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            turma = form.save(commit=False)
            turma.academia = academia
            turma.save()
            form.save_m2m()
            formset.instance = turma
            formset.save()
            return redirect('dashboard', slug=academia.slug)
    else:
        form = TurmaForm(academia=academia)
        formset = HorarioFormSet()
    contexto = {'form': form, 'formset': formset, 'tipo': 'Nova'}
    return render(request, 'core/turma_form.html', contexto)

@login_required
def turma_edit(request, pk):
    turma = get_object_or_404(Turma, pk=pk, academia=request.academia)
    HorarioFormSet = inlineformset_factory(Turma, Horario, form=HorarioForm, extra=1, can_delete=True)
    if request.method == 'POST':
        form = TurmaForm(request.POST, instance=turma, academia=request.academia)
        formset = HorarioFormSet(request.POST, instance=turma)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            return redirect('dashboard', slug=turma.academia.slug)
    else:
        form = TurmaForm(instance=turma, academia=request.academia)
        formset = HorarioFormSet(instance=turma)
    contexto = {'form': form, 'formset': formset, 'tipo': 'Editar'}
    return render(request, 'core/turma_form.html', contexto)

@login_required
def turma_delete(request, pk):
    turma = get_object_or_404(Turma, pk=pk, academia=request.academia)
    if request.method == 'POST':
        turma.delete()
    return redirect('dashboard', slug=turma.academia.slug)

# -----------------------------------------------------------------------------
# CONTROLE DE PRESENÇA
# -----------------------------------------------------------------------------

@login_required
def pagina_presenca(request, slug=None):
    academia = request.academia
    termo_busca = request.GET.get('q', '')
    alunos_ativos = Aluno.objects.filter(academia=academia, ativo=True)
    if termo_busca:
        alunos_ativos = alunos_ativos.filter(nome_completo__icontains=termo_busca)
    alunos_ativos = alunos_ativos.order_by('nome_completo')
    presentes_hoje_ids = Presenca.objects.filter(
        academia=academia, data=date.today(), aluno__in=alunos_ativos
    ).values_list('aluno_id', flat=True)
    contexto = {
        'alunos_para_chamada': alunos_ativos,
        'presentes_hoje_ids': presentes_hoje_ids,
        'data_hoje': date.today(),
        'termo_busca': termo_busca,
    }
    return render(request, 'core/pagina_presenca.html', contexto)

@login_required
def marcar_presenca_geral(request, aluno_pk, slug=None):
    if request.method == 'POST':
        academia = request.academia
        aluno = get_object_or_404(Aluno, pk=aluno_pk, academia=academia)
        Presenca.objects.get_or_create(academia=academia, aluno=aluno, data=date.today())
    return redirect('pagina_presenca', slug=request.academia_slug)

# -----------------------------------------------------------------------------
# GESTÃO FINANCEIRA (ASSINATURAS E FATURAS)
# -----------------------------------------------------------------------------

@login_required
def criar_assinatura(request, aluno_pk, slug=None):
    academia = request.academia
    aluno = get_object_or_404(Aluno, pk=aluno_pk, academia=academia)

    if request.method == 'POST':
        form = AssinaturaForm(request.POST, academia=academia)
        if form.is_valid():
            # --- Início da Lógica Principal ---
            
            # 1. Cancela assinaturas ativas antigas, se houver.
            Assinatura.objects.filter(aluno=aluno, status='ativa').update(status='cancelada')
            
            # 2. Salva a nova assinatura.
            assinatura = form.save(commit=False)
            assinatura.aluno = aluno
            assinatura.academia = academia
            assinatura.status = 'ativa'
            assinatura.save()
            
            messages.success(request, f"Assinatura do plano '{assinatura.plano.nome}' criada com sucesso para {aluno.nome_completo}!")

            # --- INÍCIO DA NOVA LÓGICA DE GERAÇÃO IMEDIATA ---
            # 3. Gera a primeira fatura para a nova assinatura.
            if aluno.dia_vencimento:
                hoje = date.today()
                dia_vencimento = aluno.dia_vencimento
                
                # Lógica de data de vencimento (igual à do comando automático)
                ano, mes = hoje.year, hoje.month
                # Se a data de início da assinatura for depois do dia de vencimento no mês atual,
                # a primeira fatura vence no mês seguinte.
                if assinatura.data_inicio.day > dia_vencimento:
                    if mes == 12: ano, mes = ano + 1, 1
                    else: mes += 1
                
                try:
                    data_vencimento_final = date(ano, mes, dia_vencimento)
                except ValueError:
                    proximo_mes = mes + 1 if mes < 12 else 1
                    proximo_ano = ano if mes < 12 else ano + 1
                    # AQUI USAMOS 'timedelta', QUE AGORA FOI IMPORTADO
                    ultimo_dia_do_mes = (date(proximo_ano, proximo_mes, 1) - timedelta(days=1)).day
                    data_vencimento_final = date(ano, mes, ultimo_dia_do_mes)

                Fatura.objects.create(
                    assinatura=assinatura,
                    academia=academia,
                    valor=assinatura.plano.valor,
                    data_vencimento=data_vencimento_final
                )
                messages.info(request, f"A primeira fatura para esta assinatura foi gerada com vencimento em {data_vencimento_final.strftime('%d/%m/%Y')}.")
            # --- FIM DA NOVA LÓGICA ---

        else:
            messages.error(request, "Não foi possível criar a assinatura. Por favor, verifique os dados do formulário.")
            
    return redirect('pagina_financeiro', slug=request.academia.slug)


@login_required
def registrar_pagamento(request, fatura_pk, slug=None):
    academia = request.academia
    fatura = get_object_or_404(Fatura, pk=fatura_pk, academia=academia)
    if request.method == 'POST':
        form = RegistrarPagamentoForm(request.POST, instance=fatura)
        if form.is_valid():
            form.save()
            # Adiciona uma mensagem de sucesso
            messages.success(request, f"Pagamento da fatura com vencimento em {fatura.data_vencimento.strftime('%d/%m/%Y')} registrado com sucesso!")
        else:
            # Adiciona uma mensagem de erro
            messages.error(request, "Não foi possível registrar o pagamento. Por favor, selecione uma data válida.")
            
    return redirect('pagina_financeiro', slug=request.academia.slug)

@login_required
def alterar_vencimento_fatura(request, fatura_pk, slug=None):
    academia = request.academia
    fatura = get_object_or_404(Fatura, pk=fatura_pk, academia=academia)
    if request.method == 'POST':
        form = AlterarVencimentoForm(request.POST, instance=fatura)
        if form.is_valid():
            form.save()
            messages.success(request, "Data de vencimento da fatura alterada com sucesso!")
        else:
            messages.error(request, "Não foi possível alterar a data. Por favor, verifique o valor informado.")
    return redirect('pagina_financeiro', slug=request.academia.slug)

# ATENÇÃO: Lembre-se de passar o novo formulário para o contexto da pagina_financeiro
@login_required
def pagina_financeiro(request, slug=None):
    academia = request.academia
    
    # 1. A variável 'alunos_ativos' é definida AQUI, no início.
    alunos_ativos = Aluno.objects.filter(academia=academia, ativo=True).order_by('nome_completo')

    # 2. A lógica percorre a lista que acabamos de criar.
    for aluno in alunos_ativos:
        assinatura_ativa = Assinatura.objects.filter(aluno=aluno, status='ativa').first()
        aluno.assinatura_ativa = assinatura_ativa
        
        aluno.status_financeiro = "Sem Plano"
        if assinatura_ativa:
            faturas_pendentes = Fatura.objects.filter(
                assinatura=assinatura_ativa, data_pagamento__isnull=True
            ).order_by('data_vencimento')
            
            aluno.faturas_pendentes = faturas_pendentes
            
            if not faturas_pendentes.exists():
                aluno.status_financeiro = "Em Dia"
            else:
                aluno.status_financeiro = "Pendente"
                for fatura in faturas_pendentes:
                    if fatura.status == "Vencida":
                        aluno.status_financeiro = "Vencida"
                        break
    
    # 3. O contexto usa a variável 'alunos_ativos' e passa para o template como 'alunos_list'.
    #    Ele também inclui todos os formulários necessários para os modais.
    contexto = {
        'alunos_list': alunos_ativos,
        'assinatura_form': AssinaturaForm(academia=academia),
        'pagamento_form': RegistrarPagamentoForm(),
        'alterar_vencimento_form': AlterarVencimentoForm(),
    }
    
    return render(request, 'core/pagina_financeiro.html', contexto)

@login_required
def cancelar_assinatura(request, assinatura_pk, slug=None):
    academia = request.academia
    assinatura = get_object_or_404(Assinatura, pk=assinatura_pk, academia=academia)
    
    if request.method == 'POST':
        assinatura.status = 'cancelada'
        assinatura.save()
        messages.warning(request, f"A assinatura do aluno {assinatura.aluno.nome_completo} foi cancelada.")
        
    return redirect('pagina_financeiro', slug=request.academia.slug)

# -----------------------------------------------------------------------------
# CADASTROS AUXILIARES (Planos, Modalidades, etc.)
# -----------------------------------------------------------------------------

@login_required
def gerenciar_cadastros(request, slug=None):
    academia = request.academia
    if request.method == 'POST':
        if 'submit_modalidade' in request.POST:
            modalidade_form = ModalidadeForm(request.POST)
            if modalidade_form.is_valid():
                modalidade = modalidade_form.save(commit=False)
                modalidade.academia = academia
                modalidade.save()
                return redirect('gerenciar_cadastros', slug=request.academia.slug)
        elif 'submit_professor' in request.POST:
            professor_form = ProfessorForm(request.POST)
            if professor_form.is_valid():
                professor = professor_form.save(commit=False)
                professor.academia = academia
                professor.save()
                return redirect('gerenciar_cadastros', slug=request.academia.slug)
    modalidade_form = ModalidadeForm()
    professor_form = ProfessorForm()
    modalidades = Modalidade.objects.filter(academia=academia)
    professores = Professor.objects.filter(academia=academia)
    contexto = {
        'modalidade_form': modalidade_form,
        'professor_form': professor_form,
        'modalidades': modalidades,
        'professores': professores,
        'academia': academia,
    }
    return render(request, 'core/gerenciar_cadastros.html', contexto)

@login_required
def deletar_modalidade(request, pk, slug=None):
    item = get_object_or_404(Modalidade, pk=pk, academia=request.academia)
    if request.method == 'POST':
        try:
            item.delete()
            messages.success(request, 'Modalidade deletada com sucesso!')
        except ProtectedError:
            messages.error(request, 'Não é possível deletar esta modalidade pois existem graduações, históricos ou exames vinculados a ela.')
    return redirect('gerenciar_cadastros', slug=request.academia.slug)

@login_required
def deletar_professor(request, pk, slug=None):
    item = get_object_or_404(Professor, pk=pk, academia=request.academia)
    if request.method == 'POST':
        try:
            item.delete()
            messages.success(request, 'Professor deletado com sucesso!')
        except ProtectedError:
            messages.error(request, 'Não é possível deletar este professor pois existem turmas ou outros registros vinculados a ele.')
    return redirect('gerenciar_cadastros', slug=request.academia.slug)

@login_required
def gerenciar_planos(request, slug=None):
    academia = request.academia
    if request.method == 'POST':
        form = PlanoForm(request.POST)
        if form.is_valid():
            plano = form.save(commit=False)
            plano.academia = academia
            plano.save()
            return redirect('gerenciar_planos', slug=request.academia.slug)
    else:
        form = PlanoForm()
    planos = Plano.objects.filter(academia=academia)
    contexto = {'form': form, 'planos': planos, 'academia': academia}
    return render(request, 'core/gerenciar_planos.html', contexto)

@login_required
def deletar_plano(request, pk, slug=None):
    plano = get_object_or_404(Plano, pk=pk, academia=request.academia)
    if request.method == 'POST':
        try:
            plano.delete()
            messages.success(request, 'Plano deletado com sucesso!')
        except ProtectedError:
            messages.error(request, 'Não é possível deletar este plano pois existem assinaturas vinculadas a ele.')
    return redirect('gerenciar_planos', slug=request.academia.slug)

@login_required
def gerenciar_dias_nao_letivos(request, slug=None):
    academia = request.academia
    if request.method == 'POST':
        form = DiaNaoLetivoForm(request.POST)
        if form.is_valid():
            dia_nao_letivo = form.save(commit=False)
            dia_nao_letivo.academia = academia
            dia_nao_letivo.save()
            return redirect('gerenciar_dias_nao_letivos', slug=request.academia.slug)
    else:
        form = DiaNaoLetivoForm()
    dias_cadastrados = DiaNaoLetivo.objects.filter(academia=academia)
    contexto = {'form': form, 'dias_cadastrados': dias_cadastrados}
    return render(request, 'core/gerenciar_dias_nao_letivos.html', contexto)

@login_required
def deletar_dia_nao_letivo(request, pk):
    dia = get_object_or_404(DiaNaoLetivo, pk=pk, academia=request.academia)
    if request.method == 'POST':
        dia.delete()
    return redirect('gerenciar_dias_nao_letivos', slug=request.academia.slug)

@login_required
def dashboard(request, slug=None):
    # A academia é obtida automaticamente do middleware
    academia = request.academia
    
    # Chama as funções de análise para obter os KPIs
    dados_financeiros = analysis.analisar_financeiro(academia)
    alunos_risco_evasao = analysis.analisar_frequencia(academia)
    
    # Os dados são filtrados automaticamente pelo TenantManager
    alunos = Aluno.objects.all()
    turmas = Turma.objects.all()
    
    contexto = {
        'academia': academia,
        'alunos': alunos,
        'turmas': turmas,
        'kpis_financeiros': dados_financeiros,
        'alunos_em_risco': alunos_risco_evasao,
    }
    
    return render(request, 'core/dashboard.html', contexto)


class AgenteIAAPIView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = PerguntaIASerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        pergunta = serializer.validated_data['question']
        academia = request.academia
        
        try:
            resposta_ia = ""
            # --- LÓGICA PARA O RESUMO INICIAL ---
            if pergunta == '__INITIAL_SUMMARY__':
                # 1. Coleta todos os dados para o resumo
                dados_financeiros = analysis.analisar_financeiro(academia)
                status_alunos = analysis.get_contagem_status_alunos(academia)
                # Busca alunos inadimplentes diretamente
                hoje = date.today()
                inadimplentes = Aluno.objects.filter(
                    academia=academia, ativo=True,
                    assinaturas__faturas__data_pagamento__isnull=True,
                    assinaturas__faturas__data_vencimento__lt=hoje
                ).distinct().values_list('nome_completo', flat=True)
                sem_assinatura = analysis.get_contagem_alunos_sem_assinatura(academia)
                ausentes = analysis.get_alunos_ausentes_recentemente(academia, dias=3)

                # 2. Monta o contexto para o prompt
                contexto_resumo = (
                    f"**Resumo Financeiro (Mês Passado):** Faturamento de R$ {dados_financeiros['faturamento_mes_passado']:.2f} e {dados_financeiros['novas_assinaturas']} nova(s) assinatura(s).\n"
                    f"**Situação Atual:** O faturamento este mês está em R$ {dados_financeiros['faturamento_mes_atual']:.2f} e a inadimplência total é de R$ {dados_financeiros['inadimplencia']:.2f}.\n"
                    f"**Quadro de Alunos:** {status_alunos['ativos']} alunos ativos e {status_alunos['inativos']} inativos.\n"
                    f"**Pontos de Atenção:**\n"
                    f"- {len(inadimplentes)} aluno(s) estão inadimplentes: {', '.join(inadimplentes) if inadimplentes else 'Nenhum'}.\n"
                    f"- {sem_assinatura} aluno(s) ativos estão sem uma assinatura ativa.\n"
                    f"- {len(ausentes)} aluno(s) não registram presença há mais de 3 dias: {', '.join(ausentes) if ausentes else 'Nenhum'}.\n"
                )
                # Dados para o boletim diário
                data_hoje = date.today().strftime('%d/%m/%Y')
                nome_dono = request.user.get_full_name() or request.user.username
                nome_assistente = "Assistente Virtual"
                cargo_assistente = "IA de Gestão"
                prompt = f"""
**Boletim Diário - {data_hoje}**

Olá {nome_dono}!

Tudo em ordem por aqui! 😄

{contexto_resumo}

Acompanharemos de perto a situação da inadimplência e as ausências para mantermos nossa ótima taxa de alunos ativos.

Qualquer dúvida, pode me chamar! 😊

Atenciosamente,

{nome_assistente} - {cargo_assistente}
"""
                # Geração da resposta para o resumo inicial
                GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
                if GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY":
                    try:
                        model = ChatGoogleGenerativeAI(
                            model="gemini-1.5-flash",
                            google_api_key=GEMINI_API_KEY,
                            temperature=0.7
                        )
                        response = model.invoke([HumanMessage(content=prompt)])
                        resposta_ia = response.content
                    except Exception as e:
                        print(f"Erro ao processar com IA: {str(e)}")
                        resposta_ia = f"Erro ao processar com IA: {str(e)}"
                else:
                    print("API Key do Gemini não configurada ou é o valor padrão.")
                    # Resposta padrão quando a API Key não está configurada
                    resposta_ia = f"""
**Boletim Diário - {data_hoje}**

Olá {nome_dono}!

Tudo em ordem por aqui! 😄

{contexto_resumo}

Acompanharemos de perto a situação da inadimplência e as ausências para mantermos nossa ótima taxa de alunos ativos.

Qualquer dúvida, pode me chamar! 😊

Atenciosamente,

{nome_assistente} - {cargo_assistente}

---
*Nota: Esta é uma resposta padrão. Para respostas personalizadas com IA, configure a variável de ambiente GEMINI_API_KEY.*
"""
            # --- LÓGICA PARA PERGUNTAS NORMAIS (LANGCHAIN) ---
            else:
                session_chat_history = request.session.get('lc_chat_history', [])
                GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
                
                if GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY":
                    try:
                        # Configura o LLM
                        llm = ChatGoogleGenerativeAI(
                            model="gemini-1.5-flash",
                            temperature=0,
                            google_api_key=GEMINI_API_KEY
                        )
                        
                        # Analisa a pergunta e busca dados específicos
                        pergunta_lower = pergunta.lower()
                        
                        if "inadimplentes" in pergunta_lower or "inadimplência" in pergunta_lower:
                            # Busca alunos inadimplentes
                            hoje = date.today()
                            inadimplentes = Aluno.objects.filter(
                                academia=academia, ativo=True,
                                assinaturas__faturas__data_pagamento__isnull=True,
                                assinaturas__faturas__data_vencimento__lt=hoje
                            ).distinct().values_list('nome_completo', flat=True)
                            
                            if inadimplentes:
                                resposta_ia = f"Alunos inadimplentes na {academia.nome_fantasia}:\n\n" + "\n".join([f"• {nome}" for nome in inadimplentes])
                            else:
                                resposta_ia = f"Ótima notícia! Não há alunos inadimplentes na {academia.nome_fantasia}."
                                
                        elif "faltoso" in pergunta_lower or "frequência" in pergunta_lower or "presença" in pergunta_lower:
                            # Busca aluno mais faltoso
                            data_limite = date.today() - timedelta(days=30)
                            alunos_ativos = Aluno.objects.filter(academia=academia, ativo=True)
                            
                            if alunos_ativos.exists():
                                alunos_com_presencas = alunos_ativos.annotate(
                                    presencas_recentes=Count('presencas', filter=Q(presencas__data__gte=data_limite))
                                ).order_by('presencas_recentes')
                                
                                aluno_mais_faltoso = alunos_com_presencas.first()
                                if aluno_mais_faltoso:
                                    resposta_ia = f"O aluno com menos presenças nos últimos 30 dias é {aluno_mais_faltoso.nome_completo}, com {aluno_mais_faltoso.presencas_recentes} presenças."
                                else:
                                    resposta_ia = "Não foi possível determinar o aluno mais faltoso."
                            else:
                                resposta_ia = "Não há alunos ativos cadastrados."
                                
                        elif "quantos alunos" in pergunta_lower or "total de alunos" in pergunta_lower:
                            # Conta alunos ativos
                            total_ativos = Aluno.objects.filter(academia=academia, ativo=True).count()
                            total_inativos = Aluno.objects.filter(academia=academia, ativo=False).count()
                            
                            resposta_ia = f"Na {academia.nome_fantasia} você tem:\n• {total_ativos} alunos ativos\n• {total_inativos} alunos inativos\n• Total: {total_ativos + total_inativos} alunos"
                            
                        elif "planos" in pergunta_lower:
                            # Lista planos
                            planos = Plano.objects.filter(academia=academia)
                            if planos.exists():
                                resposta_ia = f"Planos disponíveis na {academia.nome_fantasia}:\n\n" + "\n".join([f"• {plano.nome}: R$ {plano.valor}" for plano in planos])
                            else:
                                resposta_ia = "Nenhum plano cadastrado ainda."
                                
                        elif "nível de inadimplência" in pergunta_lower or "valor inadimplência" in pergunta_lower:
                            # Calcula inadimplência
                            hoje = date.today()
                            total_vencido = Fatura.objects.filter(
                                academia=academia,
                                data_pagamento__isnull=True,
                                data_vencimento__lt=hoje
                            ).aggregate(total=Sum('valor'))['total'] or 0
                            
                            resposta_ia = f"O valor total de faturas vencidas e não pagas na {academia.nome_fantasia} é de R$ {total_vencido:.2f}."
                            
                        else:
                            # Para outras perguntas, usa o LLM
                            prompt_text = f"""
Você é um assistente virtual especializado em gestão de academias de artes marciais.
Academia: {academia.nome_fantasia}

Com base na pergunta do usuário, forneça uma resposta útil e detalhada.
Se a pergunta for sobre dados específicos da academia, informe que essas funcionalidades estão sendo implementadas.

Pergunta do usuário: {pergunta}

Responda de forma cordial e profissional.
"""
                            
                            # Executa a pergunta diretamente com o LLM
                            response = llm.invoke([HumanMessage(content=prompt_text)])
                            resposta_ia = response.content
                        
                    except Exception as e:
                        print(f"Erro ao processar pergunta normal: {str(e)}")
                        resposta_ia = f"Desculpe, ocorreu um erro ao processar sua pergunta: {str(e)}. Por favor, tente novamente."
                else:
                    print("API Key do Gemini não configurada para perguntas normais.")
                    resposta_ia = "Desculpe, a funcionalidade de perguntas normais ainda está em desenvolvimento. Para respostas personalizadas com IA, configure a variável de ambiente GEMINI_API_KEY."

            # Define as sugestões de menu para o frontend
            sugestoes = [
                "Quem são os alunos inadimplentes?",
                "Qual o aluno mais faltoso?",
                "Listar meus planos",
                "Quantos alunos ativos tenho?",
                "Qual o nível de inadimplência?",
                "Detalhes do aluno João Silva",
                "Histórico de pagamentos do aluno Maria Santos",
            ]

            return Response({'answer': resposta_ia, 'suggestions': sugestoes}, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"ERRO NA APIView COM LANGCHAIN: {e}")
            return Response(
                {'error': 'Ocorreu um erro no servidor ao processar a pergunta com LangChain.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@login_required
def configuracao_whatsapp(request, slug=None):
    academia = request.academia
    if request.method == 'POST':
        form = ConfiguracaoWhatsAppForm(request.POST, instance=academia)
        if form.is_valid():
            form.save()
            messages.success(request, "Configurações do WhatsApp salvas com sucesso!")
            return redirect('configuracao_whatsapp', slug=request.academia.slug)
    else:
        form = ConfiguracaoWhatsAppForm(instance=academia)

    contexto = {
        'form': form
    }
    return render(request, 'core/configuracao_whatsapp.html', contexto)

@login_required
def whatsapp_conexao(request, slug=None):
    # Esta view apenas precisa renderizar o template.
    # Passamos o ID da academia para que o JavaScript saiba qual cliente gerenciar.
    academia = request.academia
    contexto = {
        'academia_id': academia.id
    }
    return render(request, 'core/whatsapp_conexao.html', contexto)

@login_required
def relatorio_frequencia(request, slug=None):
    academia = request.academia
    
    # --- Lógica dos Filtros (CORRIGIDA) ---
    data_fim = date.today()
    data_inicio = data_fim - timedelta(days=30)
    
    if request.GET.get('data_inicio'):
        data_inicio = datetime.strptime(request.GET.get('data_inicio'), '%Y-%m-%d').date()
    if request.GET.get('data_fim'):
        data_fim = datetime.strptime(request.GET.get('data_fim'), '%Y-%m-%d').date()
        
    turma_selecionada_id = request.GET.get('turma')

    # --- Lógica da Busca no Banco de Dados ---
    alunos_ativos = Aluno.objects.filter(academia=academia, ativo=True)

    filtro_presenca = Q(presencas__data__range=[data_inicio, data_fim])
    if turma_selecionada_id:
        filtro_presenca &= Q(presencas__turma_id=turma_selecionada_id)

    resultados = alunos_ativos.annotate(
        num_presencas=Count('presencas', filter=filtro_presenca)
    ).order_by('num_presencas', 'nome_completo')

    turmas_para_filtro = Turma.objects.filter(academia=academia, ativa=True)

    contexto = {
        'resultados': resultados,
        'turmas_para_filtro': turmas_para_filtro,
        'filtros_aplicados': {
            'data_inicio': data_inicio.strftime('%Y-%m-%d'),
            'data_fim': data_fim.strftime('%Y-%m-%d'),
            'turma_id': turma_selecionada_id,
        }
    }
    return render(request, 'core/relatorio_frequencia.html', contexto)

@login_required
def relatorio_financeiro(request, slug=None):
    academia = request.academia
    hoje = date.today()

    # --- Lógica dos Filtros ---
    # Define o período padrão como o mês atual
    data_inicio = hoje.replace(day=1)
    data_fim = hoje

    if request.GET.get('data_inicio'):
        data_inicio = datetime.strptime(request.GET.get('data_inicio'), '%Y-%m-%d').date()
    if request.GET.get('data_fim'):
        data_fim = datetime.strptime(request.GET.get('data_fim'), '%Y-%m-%d').date()

    status_filtro = request.GET.get('status')
    plano_filtro_id = request.GET.get('plano')

    # --- Lógica da Busca no Banco de Dados ---
    # Começa com todas as faturas do período selecionado (baseado no vencimento)
    faturas = Fatura.objects.filter(
        academia=academia,
        data_vencimento__range=[data_inicio, data_fim]
    )

    # Aplica os filtros adicionais, se existirem
    if status_filtro == 'paga':
        faturas = faturas.filter(data_pagamento__isnull=False)
    elif status_filtro == 'vencida':
        faturas = faturas.filter(data_pagamento__isnull=True, data_vencimento__lt=hoje)
    elif status_filtro == 'pendente':
        faturas = faturas.filter(data_pagamento__isnull=True, data_vencimento__gte=hoje)

    if plano_filtro_id:
        faturas = faturas.filter(assinatura__plano_id=plano_filtro_id)

    # --- Cálculo dos KPIs (Indicadores Chave) ---
    # Usamos o queryset já filtrado para os cálculos
    from decimal import Decimal
    total_recebido = faturas.filter(data_pagamento__isnull=False).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
    total_a_receber = faturas.filter(data_pagamento__isnull=True).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
    total_geral = total_recebido + total_a_receber

    # Busca os planos para popular o filtro
    planos_para_filtro = Plano.objects.filter(academia=academia)

    contexto = {
        'faturas': faturas.order_by('data_vencimento'),
        'planos_para_filtro': planos_para_filtro,
        'kpis': {
            'total_recebido': total_recebido,
            'total_a_receber': total_a_receber,
            'total_geral': total_geral,
        },
        'filtros_aplicados': {
            'data_inicio': data_inicio.strftime('%Y-%m-%d'),
            'data_fim': data_fim.strftime('%Y-%m-%d'),
            'status': status_filtro,
            'plano_id': plano_filtro_id,
        }
    }
    return render(request, 'core/relatorio_financeiro.html', contexto)

@login_required
def gerenciar_graduacoes(request, slug=None):
    academia = request.academia

    if request.method == 'POST':
        form = GraduacaoForm(request.POST, academia=academia)
        if form.is_valid():
            graduacao = form.save(commit=False)
            graduacao.academia = academia
            graduacao.save()
            messages.success(request, "Nova graduação adicionada com sucesso!")
            return redirect('gerenciar_graduacoes', slug=request.academia.slug)
    else:
        form = GraduacaoForm(academia=academia)

    # Usamos .select_related para otimizar a busca no banco de dados
    graduacoes = Graduacao.objects.filter(academia=academia).select_related('modalidade')
    contexto = {
        'form': form,
        'graduacoes': graduacoes,
    }
    return render(request, 'core/gerenciar_graduacoes.html', contexto)

@login_required
def graduacao_edit(request, pk, slug=None):
    academia = request.academia
    # Busca a graduação específica que queremos editar, garantindo que pertence à academia do usuário.
    graduacao = get_object_or_404(Graduacao, pk=pk, academia=academia)

    if request.method == 'POST':
        # Preenche o formulário com os dados enviados e com a instância existente
        form = GraduacaoForm(request.POST, instance=graduacao, academia=academia)
        if form.is_valid():
            form.save()
            messages.success(request, f"Graduação '{graduacao.nome}' atualizada com sucesso!")
            return redirect('gerenciar_graduacoes', slug=request.academia.slug)
    else:
        # Preenche o formulário com os dados atuais da graduação para exibição
        form = GraduacaoForm(instance=graduacao, academia=academia)

    contexto = {
        'form': form,
        'tipo': 'Editar' # Usaremos isso para mudar o título da página
    }
    # Vamos reutilizar o template que já temos para adicionar graduações!
    return render(request, 'core/gerenciar_graduacoes_edit.html', contexto)

@login_required
def deletar_graduacao(request, pk, slug=None):
    graduacao = get_object_or_404(Graduacao, pk=pk, academia=request.academia)
    if request.method == 'POST':
        try:
            graduacao.delete()
            messages.success(request, "Graduação removida com sucesso.")
        except models.ProtectedError:
            messages.error(request, "Esta graduação não pode ser removida pois já está associada a um ou mais alunos.")
    return redirect('gerenciar_graduacoes', slug=request.academia.slug)

@login_required
def gerenciar_exames(request, slug=None):
    academia = request.academia

    if request.method == 'POST':
        form = ExameGraduacaoForm(request.POST, academia=academia)
        if form.is_valid():
            exame = form.save(commit=False)
            exame.academia = academia
            exame.save()
            messages.success(request, "Novo exame agendado com sucesso!")
            return redirect('gerenciar_exames', slug=request.academia.slug)
    else:
        form = ExameGraduacaoForm(academia=academia)

    exames_agendados = ExameGraduacao.objects.filter(academia=academia)
    contexto = {
        'form': form,
        'exames_agendados': exames_agendados,
    }
    return render(request, 'core/gerenciar_exames.html', contexto)

@login_required
def relatorio_alunos_aptos(request, slug=None):
    academia = request.academia
    alunos_ativos = Aluno.objects.filter(academia=academia, ativo=True)

    alunos_aptos = []
    hoje = date.today()

    for aluno in alunos_ativos:
        graduacao_atual = aluno.graduacao_atual

        if not graduacao_atual:
            continue # Pula alunos sem nenhuma graduação registrada

        # Pega o registro do histórico correspondente à graduação atual
        historico_atual = aluno.historico_graduacoes.filter(graduacao=graduacao_atual).order_by('-data_promocao').first()
        if not historico_atual:
            continue

        # Calcula a data em que o aluno se tornaria apto
        data_aptidao = historico_atual.data_promocao + relativedelta(months=graduacao_atual.tempo_minimo_meses)

        # Se a data de hoje já passou da data de aptidão, ele está elegível
        if hoje >= data_aptidao:
            # Calcula há quanto tempo ele está apto
            tempo_decorrido = relativedelta(hoje, data_aptidao)
            aluno.dias_apto = tempo_decorrido.days + tempo_decorrido.months * 30 + tempo_decorrido.years * 365
            alunos_aptos.append(aluno)

    contexto = {
        'alunos_aptos': sorted(alunos_aptos, key=lambda x: x.dias_apto, reverse=True) # Ordena por quem está apto há mais tempo
    }
    return render(request, 'core/relatorio_alunos_aptos.html', contexto)

@login_required
def aluno_detalhe(request, pk):
    academia = request.academia
    aluno = get_object_or_404(Aluno, pk=pk, academia=academia)
    
    # --- LÓGICA DE PROMOÇÃO DE ALUNO (PROCESSAMENTO DO FORMULÁRIO DO MODAL) ---
    if request.method == 'POST':
        promo_form = HistoricoGraduacaoForm(request.POST, academia=academia)
        if promo_form.is_valid():
            promocao = promo_form.save(commit=False)
            promocao.aluno = aluno
            promocao.save()
            messages.success(request, f"Aluno {aluno.nome_completo} promovido com sucesso!")
            # Redireciona para a mesma página para evitar reenvio do formulário
            return redirect('aluno_detalhe', pk=aluno.pk)
    else:
        # Cria um formulário vazio para ser usado no modal
        promo_form = HistoricoGraduacaoForm(academia=academia)

    # --- LÓGICA DO CALENDÁRIO DE PRESENÇA ---
    try:
        ano = int(request.GET.get('ano', date.today().year))
        mes = int(request.GET.get('mes', date.today().month))
    except (ValueError, TypeError):
        hoje = date.today()
        ano, mes = hoje.year, hoje.month

    data_atual = date(ano, mes, 1)
    
    # Gera a matriz do calendário (ex: [[0,0,1,2,3,4,5], [6,7,...]])
    semanas_do_mes = calendar.monthcalendar(ano, mes)
    
    # Busca os dias em que houve presença neste mês
    presencas = Presenca.objects.filter(
        aluno=aluno,
        data__year=ano,
        data__month=mes
    ).values_list('data__day', flat=True)
    presencas_dias = set(presencas) # Converte para set para uma busca rápida no template

    # Lógica para navegação de meses
    mes_anterior = data_atual - timedelta(days=1)
    mes_seguinte = data_atual + relativedelta(months=1)
    
    
    # --- BUSCA DE DADOS PARA AS ABAS DO PERFIL ---
    # 1. Histórico de Graduações
    historico_graduacao = HistoricoGraduacao.objects.filter(aluno=aluno).order_by('-data_promocao')

    # 2. Histórico Financeiro (prefetch_related otimiza a busca das faturas)
    assinaturas = Assinatura.objects.filter(aluno=aluno).order_by('-data_inicio').prefetch_related('faturas')

    
    # Monta o contexto final com todos os dados para o template
    contexto = {
        'aluno': aluno,
        'promo_form': promo_form,
        'historico_graduacao': historico_graduacao,
        'assinaturas': assinaturas,
        'semanas_do_mes': semanas_do_mes,
        'presencas_dias': presencas_dias,
        'data_atual': data_atual,
        'mes_anterior': mes_anterior,
        'mes_seguinte': mes_seguinte,
    }
    
    return render(request, 'core/aluno_detalhe.html', contexto)

@login_required
def detalhe_exame(request, pk, slug=None):
    academia = request.academia
    exame = get_object_or_404(ExameGraduacao, pk=pk, academia=academia)
    
    # Busca todos os alunos já inscritos neste exame
    inscricoes = InscricaoExame.objects.filter(exame=exame).select_related('aluno', 'graduacao_pretendida')

    # --- INÍCIO DA LÓGICA CORRIGIDA ---
    
    # Pega os IDs dos alunos que já estão inscritos para podermos excluí-los da lista de "aptos a convidar"
    ids_alunos_inscritos = inscricoes.values_list('aluno_id', flat=True)

    # Começa buscando todos os alunos ativos da academia
    alunos_ativos = Aluno.objects.filter(academia=academia, ativo=True)
    
    alunos_aptos_para_convidar = []
    hoje = date.today()

    for aluno in alunos_ativos:
        # Pula o aluno se ele já estiver na lista de inscritos
        if aluno.id in ids_alunos_inscritos:
            continue

        graduacao_atual = aluno.graduacao_atual
        if not graduacao_atual:
            continue
        
        # Garante que estamos olhando apenas para alunos da mesma modalidade do exame
        if graduacao_atual.modalidade != exame.modalidade:
            continue

        historico_atual = aluno.historico_graduacoes.filter(graduacao=graduacao_atual).order_by('-data_promocao').first()
        if not historico_atual:
            continue

        data_aptidao = historico_atual.data_promocao + relativedelta(months=graduacao_atual.tempo_minimo_meses)
        
        if hoje >= data_aptidao:
            alunos_aptos_para_convidar.append(aluno)
    
    # --- FIM DA LÓGICA CORRIGIDA ---
    
    contexto = {
    'exame': exame,
    'inscricoes': inscricoes,
    'alunos_aptos_para_convidar': alunos_aptos_para_convidar,
    'reprovacao_form': ReprovacaoForm(), # Adicione esta linha
}
    return render(request, 'core/detalhe_exame.html', contexto)

@login_required
def registrar_resultado_exame(request, inscricao_pk):
    academia = request.academia
    inscricao = get_object_or_404(InscricaoExame, pk=inscricao_pk, exame__academia=academia)

    if request.method == 'POST':
        aluno = inscricao.aluno
        # Descobre qual botão foi clicado (Aprovar ou Reprovar)
        status_novo = request.POST.get("status")

        if status_novo == 'aprovado':
            inscricao.status = 'aprovado'
            inscricao.save()
            HistoricoGraduacao.objects.create(aluno=aluno, graduacao=inscricao.graduacao_pretendida)
            messages.success(request, f"{aluno.nome_completo} foi APROVADO(A) com sucesso!")

            if academia.notificar_graduacao and aluno.contato and aluno.receber_notificacoes:
                mensagem = (f"🎉 Parabéns, {aluno.nome_completo.split()[0]}! 🎉\n\nÉ com grande orgulho que a {academia.nome_fantasia} "
                            f"informa que você foi APROVADO(A) no exame de graduação!\n\n"
                            f"Sua nova graduação é **{inscricao.graduacao_pretendida.nome}**.\n\nContinue se dedicando! Oss!")
                enviar_mensagem_whatsapp(academia, aluno, mensagem, tipo='aprovacao_exame')

        elif status_novo == 'reprovado':
            form = ReprovacaoForm(request.POST, instance=inscricao)
            if form.is_valid():
                inscricao.status = 'reprovado'
                form.save() # Salva as observações
                messages.warning(request, f"O resultado de {aluno.nome_completo} foi registrado como REPROVADO(A).")

                if academia.notificar_graduacao and aluno.contato and aluno.receber_notificacoes:
                    observacoes = form.cleaned_data.get('observacoes')
                    mensagem = (f"Olá {aluno.nome_completo.split()[0]}. Passando para dar o feedback do seu exame de graduação.\n\n"
                                f"Desta vez não foi possível a aprovação, mas isso faz parte da jornada de todo grande atleta. Continue treinando e focando nos pontos abaixo e o sucesso será inevitável!\n\n"
                                f"**Pontos a melhorar:**\n{observacoes}\n\n"
                                f"Converse com seu professor. Estamos aqui para te ajudar a evoluir! Oss!")
                    enviar_mensagem_whatsapp(academia, aluno, mensagem, tipo='reprovacao_exame')

    return redirect('detalhe_exame', pk=inscricao.exame.pk)

@login_required
def convidar_alunos_exame(request, exame_pk):
    academia = request.academia
    exame = get_object_or_404(ExameGraduacao, pk=exame_pk, academia=academia)

    if request.method == 'POST':
        ids_alunos = request.POST.getlist('alunos_a_convidar')
        graduacao_id = request.POST.get('graduacao_pretendida')

        if not graduacao_id:
            messages.error(request, "Você precisa selecionar a graduação do exame.")
            return redirect('detalhe_exame', pk=exame.pk)

        graduacao = get_object_or_404(Graduacao, pk=graduacao_id)
        alunos_convidados = []

        for aluno_id in ids_alunos:
            aluno = get_object_or_404(Aluno, pk=aluno_id)
            # Cria a inscrição com o status 'convidado'
            InscricaoExame.objects.get_or_create(
                exame=exame,
                aluno=aluno,
                defaults={'graduacao_pretendida': graduacao}
            )
            alunos_convidados.append(aluno)

        messages.success(request, f"{len(alunos_convidados)} aluno(s) convidados com sucesso!")

        # --- INÍCIO DA LÓGICA DE NOTIFICAÇÃO ---
        # Verifica se a academia tem a notificação de faltas ativa (podemos usar essa mesma configuração)
        if academia.notificar_graduacao: # Ou criar um novo campo booleano em Academia
            for aluno in alunos_convidados:
                if aluno.contato and aluno.receber_notificacoes:
                    mensagem = (
                        f"Olá {aluno.nome_completo.split()[0]}! 🥋\n\n"
                        f"Temos uma ótima notícia! Você foi selecionado para participar do exame de graduação para "
                        f"**{graduacao.nome}** de {exame.modalidade.nome}.\n\n"
                        f"O exame será no dia {exame.data_exame.strftime('%d/%m/%Y às %H:%M')}.\n"
                        f"Por favor, confirme sua presença na recepção da academia.\n\n"
                        f"Parabéns pela indicação! Oss!"
                    )
                    enviar_mensagem_whatsapp(academia, aluno, mensagem, tipo='convite_exame')
        # --- FIM DA LÓGICA DE NOTIFICAÇÃO ---

    return redirect('detalhe_exame', pk=exame.pk)

@login_required
def atualizar_status_inscricao(request, inscricao_pk, novo_status):
    academia = request.academia
    inscricao = get_object_or_404(InscricaoExame, pk=inscricao_pk, exame__academia=academia)
    
    if request.method == 'POST':
        aluno = inscricao.aluno
        inscricao.status = novo_status
        inscricao.save()

        # Se o aluno foi aprovado, cria o registro no histórico E envia a notificação
        if novo_status == 'aprovado':
            HistoricoGraduacao.objects.create(
                aluno=aluno,
                graduacao=inscricao.graduacao_pretendida
            )
            messages.success(request, f"{aluno.nome_completo} foi APROVADO(A) com sucesso!")

            # --- INÍCIO DA LÓGICA DE NOTIFICAÇÃO ---
            if academia.notificar_graduacao and aluno.contato and aluno.receber_notificacoes:
                mensagem = (
                    f"🎉 Parabéns, {aluno.nome_completo.split()[0]}! 🎉\n\n"
                    f"É com grande orgulho que a {academia.nome_fantasia} informa que você foi **APROVADO(A)** "
                    f"no exame de graduação!\n\n"
                    f"Sua nova graduação é **{inscricao.graduacao_pretendida.nome}**.\n\n"
                    f"Continue se dedicando nos treinos. Estamos muito orgulhosos da sua jornada! Oss!"
                )
                enviar_mensagem_whatsapp(academia, aluno, mensagem, tipo='aprovacao_exame')
            # --- FIM DA LÓGICA DE NOTIFICAÇÃO ---

        else:
            messages.info(request, f"Status de {aluno.nome_completo} atualizado para '{novo_status}'.")

    return redirect('detalhe_exame', pk=inscricao.exame.pk)

@login_required
def deletar_exame(request, pk, slug=None):
    academia = request.academia
    # Busca o exame específico, garantindo que pertence à academia do usuário
    exame = get_object_or_404(ExameGraduacao, pk=pk, academia=academia)
    
    if request.method == 'POST':
        # Ao deletar o exame, as inscrições relacionadas (InscricaoExame)
        # também serão apagadas em cascata, devido ao on_delete=models.CASCADE.
        exame.delete()
        messages.success(request, "Exame removido com sucesso.")
        
    return redirect('gerenciar_exames', slug=request.academia.slug)

@login_required
def relatorio_mensagens(request, slug=None):
    academia = request.academia
    
    # Começa com todos os logs da academia
    log_list = LogMensagem.objects.filter(academia=academia).select_related('aluno')
    
    # --- Lógica dos Filtros ---
    termo_busca = request.GET.get('q', '')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')

    if termo_busca:
        # Busca no nome do aluno OU no conteúdo da mensagem
        log_list = log_list.filter(
            Q(aluno__nome_completo__icontains=termo_busca) |
            Q(mensagem__icontains=termo_busca)
        )

    if data_inicio:
        log_list = log_list.filter(data_envio__gte=data_inicio)
    
    if data_fim:
        # Adiciona um dia para incluir o dia final completo na busca
        data_fim_ajustada = datetime.strptime(data_fim, '%Y-%m-%d').date() + timedelta(days=1)
        log_list = log_list.filter(data_envio__lt=data_fim_ajustada)

    # --- Lógica da Paginação ---
    # Cria o objeto Paginator, mostrando 20 itens por página
    paginator = Paginator(log_list, 20)
    # Pega o número da página da URL (ex: ?page=2)
    page_number = request.GET.get('page')
    # Pega o objeto da página correspondente
    page_obj = paginator.get_page(page_number)

    contexto = {
        'page_obj': page_obj, # Enviamos o objeto da página para o template
        'filtros_aplicados': {
            'q': termo_busca,
            'data_inicio': data_inicio,
            'data_fim': data_fim,
        }
    }
    return render(request, 'core/relatorio_mensagens.html', contexto)

def sem_academia(request, slug=None):
    """ Página exibida quando o usuário não tem academia associada """
    return render(request, 'core/sem_academia.html')

@login_required
def login_redirect(request, slug=None):
    """View para redirecionar após login para o dashboard correto com slug"""
    try:
        # Busca a academia do usuário logado
        academia = Academia.objects.get(dono=request.user, ativa=True)
        return redirect('dashboard', slug=academia.slug)
    except Academia.DoesNotExist:
        return redirect('planos')
    