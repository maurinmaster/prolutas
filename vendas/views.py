from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import transaction
import stripe
import json
import os
from datetime import timedelta

from .models import Lead, SessaoVenda, CupomDesconto, ConfiguracaoVendas
from core.models import PlanoSaaS, AssinaturaSaaS, Academia
from core.forms import CustomUserCreationForm, AcademiaForm

# Configuração do Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY', 'sk_test_...')

def pagina_inicial(request):
    """Página principal do site de vendas"""
    config = ConfiguracaoVendas.get_config()
    planos = PlanoSaaS.objects.filter(ativo=True).order_by('ordem', 'preco_mensal')
    
    # Registra a sessão se não existir
    session_id = request.session.session_key
    if not session_id:
        request.session.create()
        session_id = request.session.session_key
    
    # Cria ou atualiza a sessão de venda
    sessao, created = SessaoVenda.objects.get_or_create(
        session_id=session_id,
        defaults={'pagina_inicial': request.path}
    )
    
    contexto = {
        'config': config,
        'planos': planos,
        'session_id': session_id,
    }
    return render(request, 'vendas/pagina_inicial.html', contexto)

def planos_precos(request):
    """Página de planos e preços"""
    config = ConfiguracaoVendas.get_config()
    planos = PlanoSaaS.objects.filter(ativo=True).order_by('ordem', 'preco_mensal')
    
    contexto = {
        'config': config,
        'planos': planos,
    }
    return render(request, 'vendas/planos_precos.html', contexto)

def capturar_lead(request):
    """Captura leads através de formulários"""
    if request.method == 'POST':
        nome = request.POST.get('nome')
        email = request.POST.get('email')
        telefone = request.POST.get('telefone', '')
        empresa = request.POST.get('empresa', '')
        origem = request.POST.get('origem', 'site')
        
        if nome and email:
            lead, created = Lead.objects.get_or_create(
                email=email,
                defaults={
                    'nome': nome,
                    'telefone': telefone,
                    'empresa': empresa,
                    'origem': origem,
                }
            )
            
            if not created:
                # Atualiza informações se o lead já existe
                lead.nome = nome
                lead.telefone = telefone
                lead.empresa = empresa
                lead.data_ultimo_contato = timezone.now()
                lead.save()
            
            messages.success(request, "Obrigado! Entraremos em contato em breve.")
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            
            return redirect('pagina_inicial')
    
    return redirect('pagina_inicial')

def checkout(request, plano_slug):
    """Página de checkout para um plano específico"""
    plano = get_object_or_404(PlanoSaaS, slug=plano_slug, ativo=True)
    config = ConfiguracaoVendas.get_config()
    
    # Verifica se há cupom aplicado
    cupom_codigo = request.GET.get('cupom', '')
    cupom = None
    desconto_aplicado = 0
    
    if cupom_codigo:
        try:
            cupom = CupomDesconto.objects.get(codigo=cupom_codigo.upper())
            if cupom.esta_valido:
                if cupom.desconto_fixo > 0:
                    desconto_aplicado = cupom.desconto_fixo
                else:
                    desconto_aplicado = (plano.preco_mensal * cupom.desconto_percentual) / 100
        except CupomDesconto.DoesNotExist:
            messages.error(request, "Cupom inválido.")
    
    valor_final = plano.preco_mensal - desconto_aplicado
    
    contexto = {
        'plano': plano,
        'config': config,
        'cupom': cupom,
        'desconto_aplicado': desconto_aplicado,
        'valor_final': valor_final,
    }
    return render(request, 'vendas/checkout.html', contexto)

@csrf_exempt
def criar_sessao_pagamento(request):
    """Cria uma sessão de pagamento no Stripe"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            plano_slug = data.get('plano_slug')
            ciclo_pagamento = data.get('ciclo_pagamento', 'mensal')
            cupom_codigo = data.get('cupom', '')
            
            plano = get_object_or_404(PlanoSaaS, slug=plano_slug, ativo=True)
            
            # Determina o preço baseado no ciclo
            if ciclo_pagamento == 'anual':
                preco_id = plano.stripe_price_id_anual
                valor = plano.preco_anual
            else:
                preco_id = plano.stripe_price_id_mensal
                valor = plano.preco_mensal
            
            # Aplica cupom se válido
            desconto_aplicado = 0
            if cupom_codigo:
                try:
                    cupom = CupomDesconto.objects.get(codigo=cupom_codigo.upper())
                    if cupom.esta_valido:
                        desconto_aplicado = cupom.aplicar_desconto(valor) - valor
                except CupomDesconto.DoesNotExist:
                    pass
            
            # Cria a sessão no Stripe
            session_data = {
                'payment_method_types': ['card'],
                'line_items': [{
                    'price': preco_id,
                    'quantity': 1,
                }],
                'mode': 'subscription',
                'success_url': request.build_absolute_uri('/vendas/sucesso/'),
                'cancel_url': request.build_absolute_uri('/vendas/cancelado/'),
                'metadata': {
                    'plano_slug': plano_slug,
                    'ciclo_pagamento': ciclo_pagamento,
                    'cupom_codigo': cupom_codigo,
                }
            }
            
            # Adiciona desconto se aplicável
            if desconto_aplicado > 0:
                session_data['discounts'] = [{
                    'coupon': cupom.stripe_coupon_id,
                }]
            
            session = stripe.checkout.Session.create(**session_data)
            
            return JsonResponse({
                'session_id': session.id,
                'url': session.url
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Método não permitido'}, status=405)

def sucesso_pagamento(request):
    """Página de sucesso após pagamento"""
    session_id = request.GET.get('session_id')
    
    if session_id:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            # Aqui você pode processar o sucesso do pagamento
            # e criar a assinatura no banco de dados
        except stripe.error.StripeError:
            pass
    
    return render(request, 'vendas/sucesso.html')

def cancelado_pagamento(request):
    """Página quando o pagamento é cancelado"""
    return render(request, 'vendas/cancelado.html')

@csrf_exempt
def webhook_stripe(request):
    """Webhook do Stripe para processar eventos"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.getenv('STRIPE_WEBHOOK_SECRET', 'whsec_...')
        )
    except ValueError as e:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        return HttpResponse(status=400)
    
    # Processa o evento
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        processar_pagamento_sucesso(session)
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        processar_cancelamento_assinatura(subscription)
    
    return HttpResponse(status=200)

@transaction.atomic
def processar_pagamento_sucesso(session):
    """Processa um pagamento bem-sucedido"""
    try:
        # Extrai informações da sessão
        customer_id = session.get('customer')
        subscription_id = session.get('subscription')
        metadata = session.get('metadata', {})
        
        plano_slug = metadata.get('plano_slug')
        ciclo_pagamento = metadata.get('ciclo_pagamento', 'mensal')
        
        # Busca o plano
        plano = PlanoSaaS.objects.get(slug=plano_slug, ativo=True)
        
        # Cria ou atualiza a academia (assumindo que o usuário já se cadastrou)
        # Na implementação real, você precisará associar o customer_id ao usuário
        
        # Cria a assinatura
        assinatura = AssinaturaSaaS.objects.create(
            academia=academia,  # Você precisa determinar qual academia
            plano=plano,
            status='ativa',
            stripe_customer_id=customer_id,
            stripe_subscription_id=subscription_id,
            ciclo_pagamento=ciclo_pagamento,
        )
        
        # Registra o pagamento
        from core.models import PagamentoSaaS
        PagamentoSaaS.objects.create(
            assinatura=assinatura,
            valor=session.get('amount_total', 0) / 100,  # Stripe usa centavos
            status='pago',
            stripe_payment_intent_id=session.get('payment_intent'),
            data_pagamento=timezone.now(),
            descricao=f"Pagamento inicial - {plano.nome}",
        )
        
    except Exception as e:
        print(f"Erro ao processar pagamento: {e}")

def processar_cancelamento_assinatura(subscription):
    """Processa o cancelamento de uma assinatura"""
    try:
        assinatura = AssinaturaSaaS.objects.get(
            stripe_subscription_id=subscription['id']
        )
        assinatura.status = 'cancelada'
        assinatura.data_cancelamento = timezone.now()
        assinatura.save()
    except AssinaturaSaaS.DoesNotExist:
        pass

def sobre(request):
    """Página sobre o sistema"""
    config = ConfiguracaoVendas.get_config()
    return render(request, 'vendas/sobre.html', {'config': config})

def contato(request):
    """Página de contato"""
    config = ConfiguracaoVendas.get_config()
    return render(request, 'vendas/contato.html', {'config': config})

def politica_privacidade(request):
    """Página de política de privacidade"""
    return render(request, 'vendas/politica_privacidade.html')

def termos_uso(request):
    """Página de termos de uso"""
    return render(request, 'vendas/termos_uso.html')
