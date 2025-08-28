/* =====================================================
   JAVASCRIPT ESPECÍFICO DO DASHBOARD
   ===================================================== */

(function($) {
    'use strict';

    // Namespace para dashboard
    window.ProLutas = window.ProLutas || {};
    ProLutas.Dashboard = {};

    // ===== AI ASSISTANT =====
    ProLutas.Dashboard.AIAssistant = {
        init: function() {
            this.bindEvents();
            this.showWelcomeMessage();
            this.loadSuggestions();
        },

        bindEvents: function() {
            const self = this;
            
            // Submit do formulário de pergunta
            $('#ia-question-form').on('submit', function(e) {
                e.preventDefault();
                self.submitQuestion();
            });

            // Clique nas sugestões
            $(document).on('click', '.suggestion-btn', function() {
                const question = $(this).data('question');
                $('#ia-question-input').val(question);
                self.submitQuestion();
            });

            // Limpar chat
            window.clearChat = function() {
                self.clearChat();
            };
        },

        showWelcomeMessage: function() {
            setTimeout(() => {
                this.clearWelcomeMessage();
                this.addMessage('assistant', 'Olá! 👋 Sou seu assistente virtual Pro-Lutas. Como posso ajudá-lo hoje?');
            }, 1500);
        },

        clearWelcomeMessage: function() {
            $('.welcome-message').fadeOut(300, function() {
                $(this).remove();
            });
        },

        loadSuggestions: function() {
            const suggestions = [
                { text: 'Como adicionar um novo aluno?', icon: 'bi-person-plus' },
                { text: 'Relatório de frequência', icon: 'bi-graph-up' },
                { text: 'Configurar notificações', icon: 'bi-bell' },
                { text: 'Gerenciar exames', icon: 'bi-calendar-event' }
            ];

            const suggestionsHtml = suggestions.map(s => 
                `<button class="suggestion-btn btn btn-outline-secondary btn-sm me-2 mb-2" data-question="${s.text}">
                    <i class="${s.icon} me-1"></i> ${s.text}
                </button>`
            ).join('');

            $('#ia-suggestions-area').html(`
                <div class="text-center mb-2">
                    <small class="text-muted">Sugestões rápidas:</small>
                </div>
                <div class="d-flex flex-wrap justify-content-center">
                    ${suggestionsHtml}
                </div>
            `);
        },

        submitQuestion: function() {
            const question = $('#ia-question-input').val().trim();
            if (!question) return;

            // Adiciona pergunta do usuário
            this.addMessage('user', question);
            
            // Limpa input e mostra loading
            $('#ia-question-input').val('');
            this.showTyping();
            this.setLoading(true);

            // Simula resposta (substitua por call real da API)
            setTimeout(() => {
                this.hideTyping();
                this.addMessage('assistant', this.generateResponse(question));
                this.setLoading(false);
            }, 2000);
        },

        addMessage: function(sender, message) {
            const timestamp = new Date().toLocaleTimeString('pt-BR', { 
                hour: '2-digit', 
                minute: '2-digit' 
            });

            const messageHtml = `
                <div class="message-bubble ${sender}">
                    <div class="bubble-content">
                        ${message}
                        <div class="message-timestamp">${timestamp}</div>
                    </div>
                </div>
            `;

            $('#ia-response-area').append(messageHtml);
            this.scrollToBottom();
        },

        showTyping: function() {
            const typingHtml = `
                <div class="message-bubble assistant typing-indicator">
                    <div class="bubble-content">
                        <div class="ai-typing">
                            <span class="me-2">Digitando</span>
                            <div class="typing-dots">
                                <span></span>
                                <span></span>
                                <span></span>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            $('#ia-response-area').append(typingHtml);
            this.scrollToBottom();
        },

        hideTyping: function() {
            $('.typing-indicator').remove();
        },

        setLoading: function(loading) {
            const $button = $('#ia-submit-btn');
            const $spinner = $('#ia-spinner');
            const $input = $('#ia-question-input');

            if (loading) {
                $button.prop('disabled', true);
                $spinner.show();
                $input.prop('disabled', true);
            } else {
                $button.prop('disabled', false);
                $spinner.hide();
                $input.prop('disabled', false);
            }
        },

        scrollToBottom: function() {
            const $area = $('#ia-response-area');
            $area.scrollTop($area[0].scrollHeight);
        },

        clearChat: function() {
            $('#ia-response-area').empty();
            $('#ia-suggestions-area').empty();
            this.showWelcomeMessage();
            this.loadSuggestions();
        },

        generateResponse: function(question) {
            // Respostas simuladas baseadas em palavras-chave
            const responses = {
                'aluno': 'Para adicionar um novo aluno, vá até o menu "Dashboard" e clique em "Gerenciar Cadastros". Lá você encontrará a opção de cadastrar novos alunos com todas as informações necessárias.',
                'frequência': 'Você pode acessar o relatório de frequência através do menu "Relatório de Frequência". Lá é possível filtrar por período e turma para ver o ranking de presença dos alunos.',
                'notificação': 'Para configurar notificações, acesse "Configurar Notificações" no menu lateral. Você pode configurar mensagens automáticas via WhatsApp para os alunos.',
                'exame': 'O gerenciamento de exames está disponível em "Exames de Graduação". Você pode agendar novos exames, convidar alunos aptos e registrar resultados.',
                'default': 'Entendi sua pergunta! Para informações mais específicas, consulte a documentação do sistema ou entre em contato com o suporte técnico. Posso ajudar com outras dúvidas sobre o sistema?'
            };

            // Busca por palavras-chave na pergunta
            for (const [key, response] of Object.entries(responses)) {
                if (key !== 'default' && question.toLowerCase().includes(key)) {
                    return response;
                }
            }

            return responses.default;
        }
    };

    // ===== MODAIS DO DASHBOARD =====
    ProLutas.Dashboard.Modals = {
        init: function() {
            this.bindEvents();
        },

        bindEvents: function() {
            // Modal de deletar aluno
            $('#deleteModal').on('show.bs.modal', function (event) {
                const button = $(event.relatedTarget);
                const alunoNome = button.data('aluno-nome');
                const formUrl = button.data('url');
                
                const modal = $(this);
                modal.find('#alunoNomeExcluir').text(alunoNome);
                modal.find('#deleteForm').attr('action', formUrl);
            });

            // Modal de deletar turma
            $('#deleteTurmaModal').on('show.bs.modal', function (event) {
                const button = $(event.relatedTarget);
                const turmaNome = button.data('turma-nome');
                const formUrl = button.data('url');
                
                const modal = $(this);
                modal.find('#turmaNomeExcluir').text(turmaNome);
                modal.find('#deleteTurmaForm').attr('action', formUrl);
            });
        }
    };

    // ===== FORMULÁRIOS DE TURMA =====
    ProLutas.Dashboard.TurmaForm = {
        init: function() {
            this.bindEvents();
        },

        bindEvents: function() {
            // Marcar todos os alunos
            $('#select-all-btn').on('click', function() {
                $("#id_alunos > option").prop("selected", "selected").trigger("change");
            });

            // Desmarcar todos os alunos
            $('#deselect-all-btn').on('click', function() {
                $("#id_alunos > option").prop("selected", false).trigger("change");
            });

            // Adicionar novo formulário de horário
            $('#add-horario-form').on('click', function() {
                const totalFormsInput = document.getElementById('id_horarios-TOTAL_FORMS');
                let formIdx = parseInt(totalFormsInput.value);

                const emptyFormHtml = document.getElementById('empty-form-template').innerHTML;
                const newFormHtml = emptyFormHtml.replace(/__prefix__/g, formIdx);

                $('#horarios-container').append(newFormHtml);
                totalFormsInput.value = formIdx + 1;
            });
        }
    };

    // ===== INICIALIZAÇÃO DO DASHBOARD =====
    ProLutas.Dashboard.init = function() {
        console.log('Inicializando Dashboard JS...');
        
        this.AIAssistant.init();
        this.Modals.init();
        this.TurmaForm.init();
        
        console.log('Dashboard JS inicializado!');
    };

    // Auto-init quando o documento estiver pronto
    $(document).ready(function() {
        // Só inicializa se estivermos em uma página de dashboard
        if ($('#ia-question-form').length > 0 || $('.dashboard-content').length > 0) {
            ProLutas.Dashboard.init();
        }
    });

})(jQuery);








