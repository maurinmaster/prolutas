from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
import stripe
from django.conf import settings

from .models import (
    Academia, PlanoSaaS, AssinaturaSaaS, ConfiguracaoSistema,
    PagamentoSaaS, HistoricoAssinaturaSaaS
)
from .forms import CustomUserCreationForm, AcademiaForm, CadastroAcademiaForm

# Configurar Stripe
stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')

def is_superuser(user):
    """Verifica se o usuário é superadmin"""
    return user.is_superuser

# -----------------------------------------------------------------------------
# VIEWS PÚBLICAS DO SAAS
# -----------------------------------------------------------------------------

def pagina_planos(request):
    """Página pública mostrando os planos disponíveis"""
    config = ConfiguracaoSistema.objects.first()
    
    # Verifica se o cadastro público está habilitado
    if not config or not config.permitir_cadastro_publico:
        return render(request, 'core/saas/manutencao.html')
    
    planos = PlanoSaaS.objects.filter(ativo=True).order_by('preco_mensal')
    
    context = {
        'planos': planos,
        'config': config,
    }
    
    return render(request, 'core/saas/planos.html', context)

def sobre(request):
    """Página sobre o sistema"""
    return render(request, 'core/saas/sobre.html')

def contato(request):
    """Página de contato"""
    config = ConfiguracaoSistema.objects.first()
    return render(request, 'core/saas/contato.html', {'config': config})

@transaction.atomic
def cadastro_academia(request, plano_slug=None):
    """Cadastro de nova academia com seleção de plano"""
    config = ConfiguracaoSistema.objects.first()
    
    # Verifica se o cadastro público está habilitado
    if not config or not config.permitir_cadastro_publico:
        return render(request, 'core/saas/manutencao.html')
    
    plano = None
    if plano_slug:
        plano = get_object_or_404(PlanoSaaS, slug=plano_slug, ativo=True)
    
    if request.method == 'POST':
        form = CadastroAcademiaForm(request.POST)
        plano_id = request.POST.get('plano_id')
        
        if plano_id:
            plano = get_object_or_404(PlanoSaaS, id=plano_id, ativo=True)
        
        if form.is_valid() and plano:
            from django.contrib.auth.models import User
            
            # Criar usuário
            user = User.objects.create_user(
                username=form.cleaned_data['admin_email'],
                email=form.cleaned_data['admin_email'],
                password=form.cleaned_data['admin_senha'],
                first_name=form.cleaned_data['admin_nome'].split()[0],
                last_name=' '.join(form.cleaned_data['admin_nome'].split()[1:]) if len(form.cleaned_data['admin_nome'].split()) > 1 else ''
            )
            
            # Criar academia
            academia = Academia.objects.create(
                nome=form.cleaned_data['nome'],
                slug=form.cleaned_data['slug'],
                email=form.cleaned_data['email'],
                telefone=form.cleaned_data['telefone'],
                endereco=form.cleaned_data['endereco'],
                dono=user,
                ativa=True
            )
            
            # Criar assinatura SaaS
            data_inicio = timezone.now().date()
            data_fim_trial = data_inicio + timedelta(days=config.dias_trial_padrao)
            
            assinatura = AssinaturaSaaS.objects.create(
                academia=academia,
                plano=plano,
                status='trial',
                data_inicio=data_inicio,
                data_fim_trial=data_fim_trial,
                data_vencimento=data_fim_trial,
                ciclo_pagamento='mensal'
            )
            
            # Registrar histórico
            HistoricoAssinaturaSaaS.objects.create(
                assinatura=assinatura,
                tipo_evento='criacao',
                detalhes=f'Academia criada com plano {plano.nome} em período trial'
            )
            
            # Fazer login automático
            login(request, user)
            
            messages.success(
                request, 
                f'Academia criada com sucesso! Complete o pagamento para ativar sua assinatura.'
            )
            
            # Redirecionar para pagamento
            return redirect(f'/pagamento/?academia={academia.slug}')
        
        else:
            if not plano:
                messages.error(request, 'Selecione um plano válido.')
    
    else:
        form = CadastroAcademiaForm()
    
    planos = PlanoSaaS.objects.filter(ativo=True).order_by('preco_mensal')
    
    context = {
        'form': form,
        'planos': planos,
        'plano_selecionado': plano,
        'config': config,
    }
    
    return render(request, 'core/saas/cadastro_academia.html', context)

# -----------------------------------------------------------------------------
# VIEWS DE PAGAMENTO
# -----------------------------------------------------------------------------

def pagamento(request):
    """Página de pagamento pública para academias recém-criadas"""
    academia_slug = request.GET.get('academia')
    
    if not academia_slug:
        messages.error(request, 'Academia não especificada.')
        return redirect('planos')
    
    try:
        academia = Academia.objects.get(slug=academia_slug)
        assinatura = academia.assinatura_saas
    except Academia.DoesNotExist:
        messages.error(request, 'Academia não encontrada.')
        return redirect('planos')
    
    # Verificar se já está ativa
    if assinatura.status == 'ativa':
        messages.info(request, 'Esta academia já está ativa.')
        return redirect(f'/{academia.slug}/')
    
    if request.method == 'POST':
        ciclo = request.POST.get('ciclo', 'mensal')
        
        try:
            # Criar customer no Stripe se não existir
            if not assinatura.stripe_customer_id:
                customer = stripe.Customer.create(
                    email=academia.dono.email,
                    name=academia.nome,
                    metadata={
                        'academia_id': academia.id,
                        'academia_slug': academia.slug
                    }
                )
                assinatura.stripe_customer_id = customer.id
                assinatura.save()
            
            # Determinar o preço baseado no ciclo
            if ciclo == 'anual':
                price_id = assinatura.plano.stripe_price_id_anual
                valor = assinatura.plano.preco_anual
            else:
                price_id = assinatura.plano.stripe_price_id_mensal
                valor = assinatura.plano.preco_mensal
            
            # Criar sessão de checkout
            checkout_session = stripe.checkout.Session.create(
                customer=assinatura.stripe_customer_id,
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=request.build_absolute_uri(f'/pagamento/sucesso/?academia={academia.slug}'),
                cancel_url=request.build_absolute_uri(f'/pagamento/cancelado/?academia={academia.slug}'),
                metadata={
                    'academia_id': academia.id,
                    'assinatura_id': assinatura.id,
                    'ciclo': ciclo
                }
            )
            
            return redirect(checkout_session.url)
            
        except stripe.error.StripeError as e:
            messages.error(request, f'Erro no pagamento: {str(e)}')
    
    context = {
        'academia': academia,
        'assinatura': assinatura,
    }
    
    return render(request, 'core/saas/pagamento.html', context)

@login_required
def iniciar_pagamento(request):
    """Inicia o processo de pagamento via Stripe"""
    academia = request.academia
    assinatura = academia.assinatura_saas
    
    if request.method == 'POST':
        ciclo = request.POST.get('ciclo', 'mensal')
        
        try:
            # Criar customer no Stripe se não existir
            if not assinatura.stripe_customer_id:
                customer = stripe.Customer.create(
                    email=academia.dono.email,
                    name=academia.nome_fantasia,
                    metadata={
                        'academia_id': academia.id,
                        'academia_slug': academia.slug
                    }
                )
                assinatura.stripe_customer_id = customer.id
                assinatura.save()
            
            # Determinar o preço baseado no ciclo
            if ciclo == 'anual':
                price_id = assinatura.plano.stripe_price_id_anual
                valor = assinatura.plano.preco_anual
            else:
                price_id = assinatura.plano.stripe_price_id_mensal
                valor = assinatura.plano.preco_mensal
            
            # Criar sessão de checkout
            checkout_session = stripe.checkout.Session.create(
                customer=assinatura.stripe_customer_id,
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=request.build_absolute_uri(f'/{academia.slug}/pagamento/sucesso/'),
                cancel_url=request.build_absolute_uri(f'/{academia.slug}/pagamento/cancelado/'),
                metadata={
                    'academia_id': academia.id,
                    'assinatura_id': assinatura.id,
                    'ciclo': ciclo
                }
            )
            
            return redirect(checkout_session.url)
            
        except stripe.error.StripeError as e:
            messages.error(request, f'Erro no pagamento: {str(e)}')
            return redirect(f'/{academia.slug}/')
    
    context = {
        'academia': academia,
        'assinatura': assinatura,
    }
    
    return render(request, 'core/saas/pagamento.html', context)

def pagamento_sucesso_publico(request):
    """Página pública de sucesso após pagamento"""
    academia_slug = request.GET.get('academia')
    
    if not academia_slug:
        messages.error(request, 'Academia não especificada.')
        return redirect('planos')
    
    try:
        academia = Academia.objects.get(slug=academia_slug)
    except Academia.DoesNotExist:
        messages.error(request, 'Academia não encontrada.')
        return redirect('planos')
    
    messages.success(request, 'Pagamento realizado com sucesso!')
    return render(request, 'core/saas/pagamento_sucesso.html', {'academia': academia})

def pagamento_cancelado_publico(request):
    """Página pública quando pagamento é cancelado"""
    academia_slug = request.GET.get('academia')
    
    if not academia_slug:
        messages.error(request, 'Academia não especificada.')
        return redirect('planos')
    
    try:
        academia = Academia.objects.get(slug=academia_slug)
    except Academia.DoesNotExist:
        messages.error(request, 'Academia não encontrada.')
        return redirect('planos')
    
    messages.warning(request, 'Pagamento cancelado.')
    return render(request, 'core/saas/pagamento_cancelado.html', {'academia': academia})

@login_required
def pagamento_sucesso(request):
    """Página de sucesso após pagamento (para usuários logados)"""
    academia = request.academia
    messages.success(request, 'Pagamento realizado com sucesso!')
    return render(request, 'core/saas/pagamento_sucesso.html', {'academia': academia})

@login_required
def pagamento_cancelado(request):
    """Página quando pagamento é cancelado (para usuários logados)"""
    academia = request.academia
    messages.warning(request, 'Pagamento cancelado.')
    return render(request, 'core/saas/pagamento_cancelado.html', {'academia': academia})

# -----------------------------------------------------------------------------
# WEBHOOK DO STRIPE
# -----------------------------------------------------------------------------

@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Webhook para processar eventos do Stripe"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError:
        return JsonResponse({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError:
        return JsonResponse({'error': 'Invalid signature'}, status=400)
    
    # Processar eventos
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        _processar_pagamento_sucesso(session)
    
    elif event['type'] == 'invoice.payment_succeeded':
        invoice = event['data']['object']
        _processar_pagamento_recorrente(invoice)
    
    elif event['type'] == 'invoice.payment_failed':
        invoice = event['data']['object']
        _processar_falha_pagamento(invoice)
    
    return JsonResponse({'status': 'success'})

def _processar_pagamento_sucesso(session):
    """Processa pagamento bem-sucedido"""
    try:
        assinatura_id = session['metadata']['assinatura_id']
        ciclo = session['metadata']['ciclo']
        
        assinatura = AssinaturaSaaS.objects.get(id=assinatura_id)
        assinatura.status = 'ativa'
        assinatura.ciclo_pagamento = ciclo
        assinatura.stripe_subscription_id = session['subscription']
        
        # Calcular próxima data de vencimento
        if ciclo == 'anual':
            assinatura.data_vencimento = timezone.now().date() + timedelta(days=365)
        else:
            assinatura.data_vencimento = timezone.now().date() + timedelta(days=30)
        
        assinatura.save()
        
        # Registrar pagamento
        PagamentoSaaS.objects.create(
            assinatura=assinatura,
            valor=assinatura.plano.preco_anual if ciclo == 'anual' else assinatura.plano.preco_mensal,
            status='pago',
            data_vencimento=assinatura.data_vencimento,
            data_pagamento=timezone.now().date(),
            stripe_payment_intent_id=session['payment_intent']
        )
        
        # Registrar histórico
        HistoricoAssinaturaSaaS.objects.create(
            assinatura=assinatura,
            tipo_evento='ativacao',
            detalhes=f'Assinatura ativada com ciclo {ciclo}'
        )
        
    except AssinaturaSaaS.DoesNotExist:
        pass

def _processar_pagamento_recorrente(invoice):
    """Processa pagamento recorrente"""
    try:
        subscription_id = invoice['subscription']
        assinatura = AssinaturaSaaS.objects.get(stripe_subscription_id=subscription_id)
        
        # Registrar pagamento
        PagamentoSaaS.objects.create(
            assinatura=assinatura,
            valor=invoice['amount_paid'] / 100,  # Stripe usa centavos
            status='pago',
            data_pagamento=timezone.now().date(),
            stripe_invoice_id=invoice['id']
        )
        
        # Atualizar próxima data de vencimento
        if assinatura.ciclo_pagamento == 'anual':
            assinatura.data_vencimento = timezone.now().date() + timedelta(days=365)
        else:
            assinatura.data_vencimento = timezone.now().date() + timedelta(days=30)
        
        assinatura.save()
        
    except AssinaturaSaaS.DoesNotExist:
        pass

def _processar_falha_pagamento(invoice):
    """Processa falha no pagamento"""
    try:
        subscription_id = invoice['subscription']
        assinatura = AssinaturaSaaS.objects.get(stripe_subscription_id=subscription_id)
        
        # Registrar pagamento falhado
        PagamentoSaaS.objects.create(
            assinatura=assinatura,
            valor=invoice['amount_due'] / 100,
            status='falhou',
            data_vencimento=timezone.now().date(),
            stripe_invoice_id=invoice['id']
        )
        
        # Registrar histórico
        HistoricoAssinaturaSaaS.objects.create(
            assinatura=assinatura,
            tipo_evento='falha_pagamento',
            detalhes='Falha no pagamento da assinatura'
        )
        
    except AssinaturaSaaS.DoesNotExist:
        pass

# -----------------------------------------------------------------------------
# VIEWS DE ADMINISTRAÇÃO (SUPERADMIN)
# -----------------------------------------------------------------------------

@user_passes_test(is_superuser)
def admin_dashboard(request):
    """Dashboard administrativo para superadmin - área completamente separada"""
    from django.db.models import Count, Sum
    from decimal import Decimal
    
    total_academias = Academia.objects.count()
    academias_ativas = Academia.objects.filter(ativa=True).count()
    
    # Calcular receita mensal estimada
    receita_mensal = AssinaturaSaaS.objects.filter(
        status='ativa'
    ).aggregate(
        total=Sum('plano__preco_mensal')
    )['total'] or Decimal('0.00')
    
    # Academias em trial
    academias_trial = Academia.objects.filter(
        ativa=True,
        assinatura_saas__status='trial'
    ).count()
    
    # Academias recentes (últimas 5 para o dashboard)
    academias_recentes = Academia.objects.select_related(
        'assinatura_saas__plano', 'dono'
    ).order_by('-data_cadastro')[:5]
    
    # Adicionar propriedades calculadas para as academias
    for academia in academias_recentes:
        academia.plano = academia.assinatura_saas.plano if hasattr(academia, 'assinatura_saas') else None
        academia.em_trial = academia.assinatura_saas.status == 'trial' if hasattr(academia, 'assinatura_saas') else False
        academia.criada_em = academia.data_cadastro
    
    # Alertas do sistema (exemplo)
    alertas = []
    
    # Verificar academias com trial expirando
    from datetime import date, timedelta
    trials_expirando = Academia.objects.filter(
        assinatura_saas__status='trial',
        assinatura_saas__data_fim_trial__date__lte=date.today() + timedelta(days=3)
    ).count()
    
    if trials_expirando > 0:
        alertas.append({
            'tipo': 'warning',
            'titulo': 'Trials Expirando:',
            'mensagem': f'{trials_expirando} academia(s) com trial expirando nos próximos 3 dias.'
        })
    
    context = {
        'total_academias': total_academias,
        'academias_ativas': academias_ativas,
        'receita_mensal': receita_mensal,
        'academias_trial': academias_trial,
        'academias_recentes': academias_recentes,
        'alertas': alertas,
    }
    
    return render(request, 'superadmin/dashboard.html', context)

@user_passes_test(is_superuser)
def admin_academias(request):
    """Listar e gerenciar academias"""
    academias = Academia.objects.all().select_related('dono', 'assinatura_saas__plano')
    
    context = {
        'academias': academias,
    }
    
    return render(request, 'superadmin/academias.html', context)

@user_passes_test(is_superuser)
def admin_planos(request):
    """Gerenciar planos SaaS"""
    planos = PlanoSaaS.objects.all()
    
    context = {
        'planos': planos,
    }
    
    return render(request, 'superadmin/planos.html', context)

@user_passes_test(is_superuser)
def admin_logs(request):
    """Visualizar logs do sistema"""
    context = {
        'title': 'Logs do Sistema',
    }
    return render(request, 'superadmin/logs.html', context)

@user_passes_test(is_superuser)
def admin_configuracoes(request):
    """Configurações do sistema"""
    context = {
        'title': 'Configurações do Sistema',
    }
    return render(request, 'superadmin/configuracoes.html', context)

@user_passes_test(is_superuser)
def admin_relatorios(request):
    """Relatórios do sistema"""
    context = {
        'title': 'Relatórios',
    }
    return render(request, 'superadmin/relatorios.html', context)