/* =====================================================
   JAVASCRIPT PRINCIPAL - SISTEMA PRO-LUTAS
   ===================================================== */

// Namespace global para evitar conflitos
window.ProLutas = window.ProLutas || {};

(function($) {
    'use strict';

    // ===== CONFIGURAÇÕES GLOBAIS =====
    ProLutas.config = {
        theme: {
            storageKey: 'proLutasTheme',
            defaultTheme: 'dark', // Mudança para dark como padrão
            animations: true
        },
        sidebar: {
            storageKey: 'proLutasSidebar',
            breakpoint: 992
        },
        animations: {
            duration: 300,
            easing: 'ease-in-out'
        }
    };

    // ===== GERENCIAMENTO DE TEMA =====
    ProLutas.Theme = {
        // Inicializa o sistema de tema
        init: function() {
            console.log('Inicializando sistema de tema...');
            
            // Obtém o tema salvo ou usa o padrão
            const savedTheme = localStorage.getItem(ProLutas.config.theme.storageKey);
            const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            const defaultTheme = savedTheme || (systemPrefersDark ? 'dark' : 'light');
            
            console.log(`Tema salvo: ${savedTheme}, Preferência do sistema: ${systemPrefersDark}, Tema padrão: ${defaultTheme}`);
            
            // Aplica o tema inicial UMA VEZ
            this.setTheme(defaultTheme, false);
            
            // Configura os event listeners
            this.setupEventListeners();
            
            console.log('Sistema de tema inicializado');
        },

        // Configura os event listeners
        setupEventListeners: function() {
            const self = this;
            
            // Toggle de tema
            $(document).on('click', '#theme-toggle button', function() {
                const theme = $(this).data('theme');
                console.log(`Botão de tema clicado: ${theme}`);
                self.setTheme(theme);
            });
            
            // Detecta mudança de preferência do sistema
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {
                if (!localStorage.getItem(ProLutas.config.theme.storageKey)) {
                    self.setTheme(e.matches ? 'dark' : 'light', false);
                }
            });
            
            // Listener para mudanças de tema
            $(document).on('themeChanged', function(e, theme) {
                console.log(`Evento themeChanged disparado: ${theme}`);
                
                // Aplica temas específicos com delay para evitar conflitos
                setTimeout(() => {
                    self.applyAlunosAptosTheme(theme);
                    self.applyRelatoriosTheme(theme);
                }, 100);
            });
            
            // Previne reaplicação desnecessária durante navegação
            $(window).on('beforeunload', function() {
                // Remove listeners temporariamente para evitar conflitos
                $(document).off('DOMNodeInserted');
            });
            
            // Reaplica tema quando elementos são adicionados dinamicamente (com debounce)
            let applyTimeout;
            $(document).on('DOMNodeInserted', function(e) {
                if (e.target.nodeType === 1) { // Element node
                    clearTimeout(applyTimeout);
                    applyTimeout = setTimeout(() => {
                        const currentTheme = self.getCurrentTheme();
                        self.forceThemeStyles(currentTheme);
                    }, 100);
                }
            });
        },

        // Carrega o tema salvo ou usa o padrão
        loadTheme: function() {
            const savedTheme = localStorage.getItem(ProLutas.config.theme.storageKey);
            let theme = savedTheme || ProLutas.config.theme.defaultTheme;
            
            console.log(`Tema carregado: ${theme} (salvo: ${savedTheme}, padrão: ${ProLutas.config.theme.defaultTheme})`);
            
            this.setTheme(theme, false);
        },

        // Define o tema
        setTheme: function(theme, saveToStorage = true) {
            console.log(`Definindo tema: ${theme}`);
            
            // Adiciona classe de transição para prevenir "congelamento"
            $('body').addClass('theme-transitioning');
            
            // Remove classes de tema antigas
            $('body').removeClass('theme-dark theme-light');
            
            // Aplica a nova classe
            $('body').addClass(`theme-${theme}`);
            
            // Salva no localStorage se necessário
            if (saveToStorage) {
                localStorage.setItem(ProLutas.config.theme.storageKey, theme);
            }
            
            // Força estilos inline imediatamente
            this.forceThemeStyles(theme);
            
            // Atualiza o estado dos botões
            $('#theme-toggle button').removeClass('active');
            $(`#theme-toggle button[data-theme="${theme}"]`).addClass('active');
            
            // Remove classe de transição após um pequeno delay
            setTimeout(() => {
                $('body').removeClass('theme-transitioning');
            }, 100);
            
            // Dispara evento de mudança de tema
            $(document).trigger('themeChanged', [theme]);
            
            // Aplica temas específicos com delay para evitar conflitos
            setTimeout(() => {
                this.applyAlunosAptosTheme(theme);
                this.applyRelatoriosTheme(theme);
            }, 150);
            
            console.log(`Tema definido: ${theme}`);
        },

        // Força estilos inline para garantir aplicação
        forceThemeStyles: function(theme) {
            const isDark = theme === 'dark';
            
            // Aplica estilos básicos diretamente
            $('body').css({
                'background-color': isDark ? '#1e1e1e' : '#ffffff',
                'color': isDark ? '#d4d4d4' : '#212529'
            });
            
            // Aplica estilos para cards
            $('.card').css({
                'background-color': isDark ? '#2b2b2b' : '#ffffff',
                'border-color': isDark ? '#404040' : '#dee2e6',
                'color': isDark ? '#d4d4d4' : '#212529'
            });
            
            // Aplica estilos para formulários
            $('.form-control, .form-select').css({
                'background-color': isDark ? '#2b2b2b' : '#ffffff',
                'border-color': isDark ? '#404040' : '#dee2e6',
                'color': isDark ? '#d4d4d4' : '#212529'
            });
            
            // Aplica estilos para tabelas
            $('.table').css({
                'background-color': isDark ? '#2b2b2b' : '#ffffff',
                'color': isDark ? '#d4d4d4' : '#212529'
            });
            
            // Aplica estilos para list-group
            $('.list-group-item').css({
                'background-color': isDark ? '#2b2b2b' : '#ffffff',
                'border-color': isDark ? '#404040' : '#dee2e6',
                'color': isDark ? '#d4d4d4' : '#212529'
            });
        },

        // Aplica tema a todos os elementos
        applyThemeToAllElements: function() {
            const currentTheme = this.getCurrentTheme();
            console.log(`Aplicando tema a todos os elementos: ${currentTheme}`);
            
            // Remove classes de tema antigas primeiro
            $('body').removeClass('theme-dark theme-light');
            
            // Aplica a classe do tema atual
            $('body').addClass(`theme-${currentTheme}`);
            
            // Força estilos inline como fallback
            this.forceThemeStyles(currentTheme);
            
            // Aplica tema específico para página de alunos aptos
            this.applyAlunosAptosTheme(currentTheme);
            
            // Aplica tema específico para páginas de relatório
            this.applyRelatoriosTheme(currentTheme);
            
            console.log(`Tema aplicado a todos os elementos: ${currentTheme}`);
        },

        // Aplica tema específico para página de alunos aptos
        applyAlunosAptosTheme: function(theme) {
            const isDark = theme === 'dark';
            
            // Verifica se está na página de alunos aptos
            if (window.location.pathname.includes('relatorio_alunos_aptos') || 
                document.title.includes('Alunos Aptos')) {
                
                console.log('Aplicando tema específico para página de alunos aptos...');
                
                // Força cores das linhas da tabela
                $('.table-row').css({
                    'background-color': isDark ? '#2b2b2b' : '#ffffff',
                    'color': isDark ? '#d4d4d4' : '#212529'
                });
                
                // Força cores das células da tabela
                $('.table-row td').css({
                    'background-color': 'transparent',
                    'color': isDark ? '#d4d4d4' : '#212529',
                    'border-color': isDark ? '#404040' : '#dee2e6'
                });
                
                // Força cores dos elementos de texto
                $('.table-row .student-name').css('color', isDark ? '#d4d4d4' : '#212529');
                $('.table-row .student-meta').css('color', isDark ? '#6d6d6d' : '#6c757d');
                $('.table-row .fw-medium').css('color', isDark ? '#d4d4d4' : '#212529');
                
                // Força cores dos status badges
                $('.status-badge.status-success').css({
                    'background-color': isDark ? 'rgba(78, 201, 176, 0.15)' : 'rgba(40, 167, 69, 0.1)',
                    'color': isDark ? '#4ec9b0' : '#28a745',
                    'border-color': isDark ? 'rgba(78, 201, 176, 0.3)' : 'rgba(40, 167, 69, 0.25)'
                });
                
                // Força cores dos avatars
                $('.student-avatar').css('border-color', isDark ? '#404040' : '#dee2e6');
                $('.student-avatar-placeholder').css({
                    'background-color': isDark ? '#363636' : '#f8f9fa',
                    'border-color': isDark ? '#404040' : '#dee2e6',
                    'color': isDark ? '#6d6d6d' : '#6c757d'
                });
                
                // Força cores dos ícones
                $('.table-row .bi-person-badge').css('color', isDark ? '#6d6d6d' : '#6c757d');
                $('.table-row .bi-award').css('color', isDark ? '#ce9178' : '#ffc107');
                $('.table-row .bi-check-circle').css('color', isDark ? '#4ec9b0' : '#28a745');
                
                // Força cores do alert info
                $('.alert-info').css({
                    'background-color': isDark ? 'rgba(86, 156, 214, 0.15)' : 'rgba(0, 102, 204, 0.1)',
                    'color': isDark ? '#569cd6' : '#0066cc',
                    'border-color': isDark ? 'rgba(86, 156, 214, 0.3)' : 'rgba(0, 102, 204, 0.25)'
                });
                
                // Força cores do empty state
                $('.empty-state-icon').css('color', isDark ? '#6d6d6d' : '#6c757d');
                $('.empty-state h5').css('color', isDark ? '#9d9d9d' : '#495057');
                $('.empty-state p').css('color', isDark ? '#6d6d6d' : '#6c757d');
                $('.empty-state small').css('color', isDark ? '#6d6d6d' : '#6c757d');
                
                // Força cores da futuristic table
                $('.futuristic-table-container').css({
                    'background-color': isDark ? '#2b2b2b' : '#ffffff',
                    'border-color': isDark ? '#404040' : '#dee2e6'
                });
                
                $('.futuristic-table tbody tr').css({
                    'background-color': isDark ? '#2b2b2b' : '#ffffff',
                    'color': isDark ? '#d4d4d4' : '#212529'
                });
                
                $('.futuristic-table tbody tr:hover').css('background-color', isDark ? '#363636' : '#f5f5f5');
                
                $('.futuristic-table thead th').css({
                    'background-color': isDark ? '#252525' : '#f8f9fa',
                    'color': isDark ? '#9d9d9d' : '#495057',
                    'border-bottom-color': isDark ? '#404040' : '#dee2e6'
                });
                
                console.log('Tema específico para alunos aptos aplicado');
            }
        },

        // Aplica tema específico para páginas de relatório
        applyRelatoriosTheme: function(theme) {
            const isDark = theme === 'dark';
            
            // Verifica se está em alguma página de relatório
            if (window.location.pathname.includes('relatorio_frequencia') || 
                window.location.pathname.includes('relatorio_financeiro') ||
                window.location.pathname.includes('relatorio_mensagens') ||
                document.title.includes('Relatório')) {
                
                console.log('Aplicando tema específico para páginas de relatório...');
                
                // Força cores das tabelas de relatório
                $('.table-hover tbody tr, .table-sm tbody tr').css({
                    'background-color': isDark ? '#2b2b2b' : '#ffffff',
                    'color': isDark ? '#d4d4d4' : '#212529'
                });
                
                $('.table-hover tbody tr:hover, .table-sm tbody tr:hover').css('background-color', isDark ? '#363636' : '#f5f5f5');
                
                $('.table-hover tbody td, .table-sm tbody td').css({
                    'background-color': 'transparent',
                    'color': isDark ? '#d4d4d4' : '#212529',
                    'border-color': isDark ? '#404040' : '#dee2e6'
                });
                
                $('.table-hover thead th, .table-sm thead th').css({
                    'background-color': isDark ? '#252525' : '#f8f9fa',
                    'color': isDark ? '#9d9d9d' : '#495057',
                    'border-bottom-color': isDark ? '#404040' : '#dee2e6'
                });
                
                // Força cores dos KPIs financeiros
                $('.card-subtitle').css('color', isDark ? '#6d6d6d' : '#6c757d');
                $('.text-success').css('color', isDark ? '#4ec9b0' : '#28a745');
                $('.text-warning').css('color', isDark ? '#ce9178' : '#ffc107');
                $('.fw-bold').css('color', isDark ? '#d4d4d4' : '#212529');
                
                // Força cores dos badges
                $('.bg-success').css({
                    'background-color': isDark ? 'rgba(78, 201, 176, 0.15)' : 'rgba(40, 167, 69, 0.1)',
                    'color': isDark ? '#4ec9b0' : '#28a745',
                    'border-color': isDark ? 'rgba(78, 201, 176, 0.3)' : 'rgba(40, 167, 69, 0.25)'
                });
                
                $('.bg-danger').css({
                    'background-color': isDark ? 'rgba(244, 135, 113, 0.15)' : 'rgba(220, 53, 69, 0.1)',
                    'color': isDark ? '#f48771' : '#dc3545',
                    'border-color': isDark ? 'rgba(244, 135, 113, 0.3)' : 'rgba(220, 53, 69, 0.25)'
                });
                
                $('.bg-warning').css({
                    'background-color': isDark ? 'rgba(206, 145, 120, 0.15)' : 'rgba(255, 193, 7, 0.1)',
                    'color': isDark ? '#ce9178' : '#ffc107',
                    'border-color': isDark ? 'rgba(206, 145, 120, 0.3)' : 'rgba(255, 193, 7, 0.25)'
                });
                
                $('.text-dark').css('color', isDark ? '#d4d4d4' : '#212529');
                
                // Força cores dos elementos específicos do log de mensagens
                if (window.location.pathname.includes('relatorio_mensagens')) {
                    $('.report-header').css({
                        'background-color': isDark ? '#1e1e1e' : '#ffffff',
                        'border-color': isDark ? '#569cd6' : '#0066cc',
                        'border-width': '2px',
                        'color': isDark ? '#d4d4d4' : '#212529',
                        'box-shadow': isDark ? '0 4px 12px rgba(0, 0, 0, 0.3)' : '0 4px 12px rgba(0, 0, 0, 0.1)'
                    });
                    
                    $('.report-title').css({
                        'color': isDark ? '#ffffff' : '#212529',
                        'font-weight': '700',
                        'text-shadow': isDark ? '0 2px 4px rgba(0, 0, 0, 0.3)' : 'none'
                    });
                    
                    $('.report-icon').css('color', isDark ? '#c586c0' : '#6f42c1');
                    
                    $('.search-card').css({
                        'background-color': isDark ? '#2b2b2b' : '#ffffff',
                        'border-color': isDark ? '#569cd6' : '#0066cc',
                        'border-width': '2px',
                        'box-shadow': isDark ? '0 4px 12px rgba(0, 0, 0, 0.3)' : '0 4px 12px rgba(0, 0, 0, 0.1)'
                    });
                    
                    $('.search-btn').css({
                        'background-color': isDark ? '#569cd6' : '#0066cc',
                        'border-color': isDark ? '#569cd6' : '#0066cc',
                        'color': isDark ? '#1e1e1e' : '#ffffff'
                    });
                    
                    $('.messages-table').css('background-color', isDark ? '#2b2b2b' : '#ffffff');
                    
                    $('.messages-table th').css({
                        'background-color': isDark ? '#1e1e1e' : '#f8f9fa',
                        'color': isDark ? '#ffffff' : '#495057',
                        'font-weight': '600',
                        'text-transform': 'uppercase',
                        'letter-spacing': '0.5px',
                        'border-bottom': isDark ? '2px solid #569cd6' : '2px solid #0066cc',
                        'text-shadow': isDark ? '0 1px 2px rgba(0, 0, 0, 0.3)' : 'none'
                    });
                    
                    $('.messages-table tbody tr').css({
                        'border-bottom-color': isDark ? '#404040' : '#dee2e6',
                        'border-bottom-width': isDark ? '2px' : '1px',
                        'border-bottom-style': 'solid',
                        'background-color': isDark ? '#2b2b2b' : '#ffffff',
                        'color': isDark ? '#d4d4d4' : '#212529'
                    });
                    
                    $('.messages-table tbody tr:hover').css({
                        'background-color': isDark ? '#404040' : '#f5f5f5',
                        'box-shadow': isDark ? '0 2px 8px rgba(0, 0, 0, 0.3)' : '0 2px 8px rgba(0, 0, 0, 0.1)',
                        'transform': 'translateY(-1px)',
                        'transition': 'all 0.2s ease'
                    });
                    
                    $('.messages-table td').css('color', isDark ? '#d4d4d4' : '#212529');
                    
                    // Data/hora mais destacada
                    $('.messages-table td:first-child').css({
                        'font-weight': '600',
                        'color': isDark ? '#ffffff' : '#212529'
                    });
                    
                    $('.messages-table td:first-child small').css({
                        'color': isDark ? '#9d9d9d' : '#6c757d',
                        'font-weight': '400'
                    });
                    
                    // Nome do aluno mais destacado
                    $('.messages-table td:nth-child(2)').css({
                        'font-weight': '600',
                        'color': isDark ? '#ffffff' : '#212529'
                    });
                    
                    $('.messages-table td:nth-child(2) small').css({
                        'color': isDark ? '#9d9d9d' : '#6c757d',
                        'font-weight': '400'
                    });
                    
                    $('.status-success').css({
                        'background-color': isDark ? 'rgba(78, 201, 176, 0.25)' : 'rgba(40, 167, 69, 0.1)',
                        'color': isDark ? '#4ec9b0' : '#28a745',
                        'border-color': isDark ? '#4ec9b0' : '#28a745',
                        'border-width': '2px',
                        'font-weight': '600',
                        'text-shadow': isDark ? '0 1px 2px rgba(0, 0, 0, 0.3)' : 'none',
                        'box-shadow': isDark ? '0 2px 4px rgba(78, 201, 176, 0.2)' : 'none'
                    });
                    
                    $('.status-error').css({
                        'background-color': isDark ? 'rgba(244, 135, 113, 0.25)' : 'rgba(220, 53, 69, 0.1)',
                        'color': isDark ? '#f48771' : '#dc3545',
                        'border-color': isDark ? '#f48771' : '#dc3545',
                        'border-width': '2px',
                        'font-weight': '600',
                        'text-shadow': isDark ? '0 1px 2px rgba(0, 0, 0, 0.3)' : 'none',
                        'box-shadow': isDark ? '0 2px 4px rgba(244, 135, 113, 0.2)' : 'none'
                    });
                    
                    $('.type-badge').css({
                        'background-color': isDark ? '#404040' : '#e9ecef',
                        'color': isDark ? '#d4d4d4' : '#495057',
                        'border-color': isDark ? '#569cd6' : '#0066cc',
                        'border-width': '1px',
                        'border-style': 'solid',
                        'font-weight': '600',
                        'text-shadow': isDark ? '0 1px 2px rgba(0, 0, 0, 0.3)' : 'none'
                    });
                    
                    $('.message-content').css({
                        'background-color': isDark ? '#2b2b2b' : '#f8f9fa',
                        'border-color': isDark ? '#404040' : '#dee2e6',
                        'color': isDark ? '#e0e0e0' : '#495057',
                        'border-width': '1px',
                        'border-style': 'solid',
                        'box-shadow': isDark ? 'inset 0 1px 3px rgba(0, 0, 0, 0.2)' : 'none'
                    });
                    
                    $('.empty-state').css({
                        'background-color': isDark ? '#2b2b2b' : '#f8f9fa',
                        'color': isDark ? '#9d9d9d' : '#6c757d',
                        'border-color': isDark ? '#404040' : '#dee2e6',
                        'border-width': '2px',
                        'box-shadow': isDark ? 'inset 0 2px 8px rgba(0, 0, 0, 0.2)' : 'none'
                    });
                    
                    $('.empty-state h5').css({
                        'color': isDark ? '#ffffff' : '#495057',
                        'font-weight': '600'
                    });
                    
                    $('.empty-state p').css({
                        'color': isDark ? '#b0b0b0' : '#6c757d',
                        'font-weight': '500'
                    });
                    
                    $('.empty-state small').css({
                        'color': isDark ? '#9d9d9d' : '#6c757d',
                        'font-weight': '400'
                    });
                    
                    $('.border-top').css('border-color', isDark ? '#404040' : '#dee2e6');
                    
                    // Ícones mais visíveis
                    $('.messages-table .bi').css({
                        'filter': isDark ? 'drop-shadow(0 1px 2px rgba(0, 0, 0, 0.3))' : 'none'
                    });
                }
                
                // Força cores dos ícones específicos
                $('.bi-graph-up, .bi-filter, .bi-bar-chart-line-fill').css('color', isDark ? '#569cd6' : '#0066cc');
                $('.bi-chat-left-text-fill').css('color', isDark ? '#c586c0' : '#6f42c1');
                $('.bi-info-circle, .bi-search, .bi-calendar-event, .bi-calendar-check').css('color', isDark ? '#569cd6' : '#0066cc');
                $('.bi-check-circle').css('color', isDark ? '#4ec9b0' : '#28a745');
                $('.bi-x-circle').css('color', isDark ? '#f48771' : '#dc3545');
                $('.bi-person-badge').css('color', isDark ? '#6d6d6d' : '#6c757d');
                $('.bi-chat-x').css('color', isDark ? '#6d6d6d' : '#6c757d');
                
                console.log('Tema específico para relatórios aplicado');
            }
        },

        // Obtém o tema atual
        getCurrentTheme: function() {
            return $('body').hasClass('theme-dark') ? 'dark' : 'light';
        },

        // Cria o toggle de tema
        createThemeToggle: function() {
            const currentTheme = this.getCurrentTheme();
            
            // Remove toggle existente se houver
            $('#theme-toggle').remove();
            
            // Cria o novo toggle
            const toggleHtml = `
                <div id="theme-toggle" class="theme-toggle">
                    <button data-theme="light" class="${currentTheme === 'light' ? 'active' : ''}" title="Tema Claro">
                        <i class="bi bi-sun-fill"></i>
                    </button>
                    <button data-theme="dark" class="${currentTheme === 'dark' ? 'active' : ''}" title="Tema Escuro">
                        <i class="bi bi-moon-fill"></i>
                    </button>
                </div>
            `;
            
            $('body').append(toggleHtml);
            console.log('Toggle de tema criado');
        },

        // Vincula eventos do tema
        bindEvents: function() {
            const self = this;
            
            // Toggle de tema
            $(document).on('click', '#theme-toggle button', function() {
                const theme = $(this).data('theme');
                console.log(`Botão de tema clicado: ${theme}`);
                self.setTheme(theme);
                
                // Aplica tema específico para alunos aptos se necessário
                setTimeout(() => {
                    self.applyAlunosAptosTheme(theme);
                }, 150);
                
                // Aplica tema específico para relatórios se necessário
                setTimeout(() => {
                    self.applyRelatoriosTheme(theme);
                }, 150);
            });
            
            // Detecta mudança de preferência do sistema
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {
                if (!localStorage.getItem(ProLutas.config.theme.storageKey)) {
                    self.setTheme(e.matches ? 'dark' : 'light', false);
                    
                    // Aplica tema específico para alunos aptos se necessário
                    setTimeout(() => {
                        self.applyAlunosAptosTheme(e.matches ? 'dark' : 'light');
                    }, 150);
                    
                    // Aplica tema específico para relatórios se necessário
                    setTimeout(() => {
                        self.applyRelatoriosTheme(e.matches ? 'dark' : 'light');
                    }, 150);
                }
            });
            
            // Reaplica tema quando elementos são adicionados dinamicamente
            $(document).on('DOMNodeInserted', function(e) {
                if (e.target.nodeType === 1) { // Element node
                    setTimeout(() => {
                        self.applyThemeToAllElements();
                    }, 50);
                }
            });
            
            // Listener para mudanças de tema
            $(document).on('themeChanged', function(e, theme) {
                console.log(`Evento themeChanged disparado: ${theme}`);
                
                // Aplica tema específico para alunos aptos se necessário
                setTimeout(() => {
                    self.applyAlunosAptosTheme(theme);
                }, 100);
                
                // Aplica tema específico para relatórios se necessário
                setTimeout(() => {
                    self.applyRelatoriosTheme(theme);
                }, 100);
            });
            
            console.log('Eventos do tema vinculados');
        }
    };

    // ===== GERENCIAMENTO DA SIDEBAR =====
    ProLutas.Sidebar = {
        init: function() {
            this.bindEvents();
            this.handleResize();
        },

        bindEvents: function() {
            const self = this;
            
            // Toggle da sidebar em dispositivos móveis
            $(document).on('click', '#menu-toggle', function() {
                self.toggle();
            });
            
            // Fecha sidebar ao clicar fora (mobile)
            $(document).on('click', function(e) {
                if (window.innerWidth <= ProLutas.config.sidebar.breakpoint) {
                    if (!$(e.target).closest('.sidebar, #menu-toggle').length) {
                        self.close();
                    }
                }
            });
            
            // Resize handler
            $(window).on('resize', function() {
                self.handleResize();
            });
        },

        toggle: function() {
            $('.sidebar').toggleClass('active');
        },

        close: function() {
            $('.sidebar').removeClass('active');
        },

        open: function() {
            $('.sidebar').addClass('active');
        },

        handleResize: function() {
            if (window.innerWidth > ProLutas.config.sidebar.breakpoint) {
                $('.sidebar').removeClass('active');
            }
        }
    };

    // ===== UTILITÁRIOS GERAIS =====
    ProLutas.Utils = {
        // Formata números para exibição
        formatNumber: function(number, decimals = 0) {
            return new Intl.NumberFormat('pt-BR', {
                minimumFractionDigits: decimals,
                maximumFractionDigits: decimals
            }).format(number);
        },

        // Formata moeda
        formatCurrency: function(value) {
            return new Intl.NumberFormat('pt-BR', {
                style: 'currency',
                currency: 'BRL'
            }).format(value);
        },

        // Formata datas
        formatDate: function(date, options = {}) {
            const defaultOptions = {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit'
            };
            
            return new Intl.DateTimeFormat('pt-BR', { ...defaultOptions, ...options }).format(new Date(date));
        },

        // Debounce function
        debounce: function(func, wait, immediate) {
            let timeout;
            return function executedFunction() {
                const context = this;
                const args = arguments;
                const later = function() {
                    timeout = null;
                    if (!immediate) func.apply(context, args);
                };
                const callNow = immediate && !timeout;
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
                if (callNow) func.apply(context, args);
            };
        },

        // Mostra notificação toast
        showToast: function(message, type = 'info', duration = 5000) {
            const toastHtml = `
                <div class="toast align-items-center border-0 toast-${type}" role="alert" aria-live="assertive" aria-atomic="true">
                    <div class="d-flex">
                        <div class="toast-body">
                            ${message}
                        </div>
                        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                    </div>
                </div>
            `;
            
            // Cria container se não existir
            if ($('#toast-container').length === 0) {
                $('body').append('<div id="toast-container" class="toast-container position-fixed top-0 end-0 p-3" style="z-index: 1055;"></div>');
            }
            
            const $toast = $(toastHtml);
            $('#toast-container').append($toast);
            
            // Inicializa e mostra o toast
            const toast = new bootstrap.Toast($toast[0], { delay: duration });
            toast.show();
            
            // Remove do DOM após esconder
            $toast.on('hidden.bs.toast', function() {
                $(this).remove();
            });
        },

        // Confirma ação
        confirmAction: function(message, callback) {
            if (confirm(message)) {
                callback();
            }
        }
    };

    // ===== COMPONENTES ESPECÍFICOS =====
    ProLutas.Components = {
        // Inicializa Select2
        initSelect2: function() {
            if (typeof $.fn.select2 !== 'undefined') {
                $('.select2-widget').select2({
                    theme: "bootstrap-5",
                    placeholder: "Selecione uma ou mais opções",
                    closeOnSelect: false,
                    language: {
                        noResults: function() {
                            return "Nenhum resultado encontrado";
                        },
                        searching: function() {
                            return "Buscando...";
                        }
                    }
                });
            }
        },

        // Inicializa tooltips
        initTooltips: function() {
            if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
                const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
                tooltipTriggerList.map(function (tooltipTriggerEl) {
                    return new bootstrap.Tooltip(tooltipTriggerEl);
                });
            }
        },

        // Inicializa popovers
        initPopovers: function() {
            if (typeof bootstrap !== 'undefined' && bootstrap.Popover) {
                const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
                popoverTriggerList.map(function (popoverTriggerEl) {
                    return new bootstrap.Popover(popoverTriggerEl);
                });
            }
        },

        // Inicializa animações AOS se disponível
        initAOS: function() {
            if (typeof AOS !== 'undefined') {
                AOS.init({
                    duration: 800,
                    once: true,
                    offset: 100
                });
            }
        },

        // Máscaras de input
        initMasks: function() {
            // Telefone
            $('.mask-phone').on('input', function() {
                let value = this.value.replace(/\D/g, '');
                if (value.length <= 10) {
                    value = value.replace(/(\d{2})(\d{4})(\d{4})/, '($1) $2-$3');
                } else {
                    value = value.replace(/(\d{2})(\d{5})(\d{4})/, '($1) $2-$3');
                }
                this.value = value;
            });

            // CPF
            $('.mask-cpf').on('input', function() {
                let value = this.value.replace(/\D/g, '');
                value = value.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
                this.value = value;
            });

            // Moeda
            $('.mask-currency').on('input', function() {
                let value = this.value.replace(/\D/g, '');
                value = (value / 100).toFixed(2).replace('.', ',');
                value = value.replace(/(\d)(?=(\d{3})+(?!\d))/g, '$1.');
                this.value = 'R$ ' + value;
            });
        }
    };

    // ===== FORMS =====
    ProLutas.Forms = {
        // Inicializa funcionalidades de formulários
        init: function() {
            this.bindValidation();
            this.bindSubmit();
        },

        // Validação em tempo real
        bindValidation: function() {
            // Validação de campos obrigatórios
            $('form input[required], form select[required], form textarea[required]').on('blur', function() {
                const $field = $(this);
                const value = $field.val();
                
                if (!value || value.trim() === '') {
                    $field.addClass('is-invalid');
                } else {
                    $field.removeClass('is-invalid').addClass('is-valid');
                }
            });

            // Validação de email
            $('input[type="email"]').on('blur', function() {
                const $field = $(this);
                const email = $field.val();
                const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                
                if (email && !emailRegex.test(email)) {
                    $field.addClass('is-invalid');
                } else if (email) {
                    $field.removeClass('is-invalid').addClass('is-valid');
                }
            });
        },

        // Submit de formulários
        bindSubmit: function() {
            $('form').on('submit', function() {
                const $form = $(this);
                const $submitBtn = $form.find('button[type="submit"]');
                
                // Previne duplo submit
                $submitBtn.prop('disabled', true);
                
                // Reabilita após 3 segundos (fallback)
                setTimeout(function() {
                    $submitBtn.prop('disabled', false);
                }, 3000);
            });
        }
    };

    // Inicialização principal
    ProLutas.init = function() {
        console.log('Inicializando ProLutas...');
        
        // Inicializa o sistema de tema
        ProLutas.Theme.init();
        
        // Cria o toggle de tema
        ProLutas.Theme.createThemeToggle();
        
        // Aplica temas específicos para páginas especiais
        ProLutas.applySpecialPageThemes();
        
        console.log('ProLutas inicializado');
    };

    // Aplica temas específicos para páginas especiais
    ProLutas.applySpecialPageThemes = function() {
        // Aplica tema específico para página de alunos aptos
        if (window.location.pathname.includes('relatorio_alunos_aptos') || 
            document.title.includes('Alunos Aptos')) {
            
            console.log('Detectada página de alunos aptos - aplicando tema específico...');
            
            // Aguarda um pouco para garantir que o DOM esteja pronto
            setTimeout(() => {
                ProLutas.Theme.applyAlunosAptosTheme(ProLutas.Theme.getCurrentTheme());
            }, 100);
            
            // Aplica novamente após um delay maior para garantir
            setTimeout(() => {
                ProLutas.Theme.applyAlunosAptosTheme(ProLutas.Theme.getCurrentTheme());
            }, 500);
        }
        
        // Aplica tema específico para páginas de relatório
        if (window.location.pathname.includes('relatorio_frequencia') || 
            window.location.pathname.includes('relatorio_financeiro') ||
            window.location.pathname.includes('relatorio_mensagens') ||
            document.title.includes('Relatório')) {
            
            console.log('Detectada página de relatório - aplicando tema específico...');
            
            // Aguarda um pouco para garantir que o DOM esteja pronto
            setTimeout(() => {
                ProLutas.Theme.applyRelatoriosTheme(ProLutas.Theme.getCurrentTheme());
            }, 100);
            
            // Aplica novamente após um delay maior para garantir
            setTimeout(() => {
                ProLutas.Theme.applyRelatoriosTheme(ProLutas.Theme.getCurrentTheme());
            }, 500);
        }
    };

    // Previne flash durante navegação
    ProLutas.preventThemeFlash = function() {
        // Aplica o tema imediatamente no head para evitar flash
        const savedTheme = localStorage.getItem(ProLutas.config.theme.storageKey);
        const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        const defaultTheme = savedTheme || (systemPrefersDark ? 'dark' : 'light');
        
        // Adiciona classe ao body imediatamente
        document.body.className = document.body.className.replace(/theme-\w+/g, '') + ` theme-${defaultTheme}`;
        
        // Adiciona estilos críticos inline para evitar flash
        const criticalStyles = document.createElement('style');
        criticalStyles.textContent = `
            body.theme-dark {
                background-color: #1e1e1e !important;
                color: #d4d4d4 !important;
            }
            body.theme-light {
                background-color: #ffffff !important;
                color: #212529 !important;
            }
        `;
        document.head.appendChild(criticalStyles);
        
        console.log(`Tema crítico aplicado: ${defaultTheme}`);
    };

    // ===== AUTO-INIT =====
    $(document).ready(function() {
        // Previne flash de tema imediatamente
        ProLutas.preventThemeFlash();
        
        // Inicializa o sistema
        ProLutas.init();
    });

})(jQuery);

// ===== FUNÇÕES GLOBAIS PARA COMPATIBILIDADE =====

// Toggle de tema (para compatibilidade)
function toggleTheme() {
    const currentTheme = ProLutas.Theme.getCurrentTheme();
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    ProLutas.Theme.setTheme(newTheme);
}

// Mostrar notificação
function showNotification(message, type = 'info') {
    ProLutas.Utils.showToast(message, type);
}

// Confirmar ação
function confirmDelete(message, callback) {
    ProLutas.Utils.confirmAction(message || 'Tem certeza que deseja excluir?', callback);
}
