// whatsapp_gateway/index.js

const express = require('express');
const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode');
const cors = require('cors');
const fs = require('fs');
const path = require('path');

// --- 1. CONFIGURAÇÃO INICIAL ---
const app = express();
const port = 3000;

// 1. PRIMEIRO, ensine o Express a ler JSON.
app.use(express.json()); 

// 2. DEPOIS, aplique as permissões de CORS.
app.use(cors()); 

// --- FUNÇÃO PARA LIMPAR SESSÕES ANTIGAS ---
function cleanupOldSessions() {
    const authDir = path.join(__dirname, '.wwebjs_auth');
    if (fs.existsSync(authDir)) {
        try {
            const sessions = fs.readdirSync(authDir);
            sessions.forEach(session => {
                const sessionPath = path.join(authDir, session);
                if (fs.statSync(sessionPath).isDirectory()) {
                    // Tenta limpar arquivos de cookies que podem estar bloqueados
                    const cookiesPath = path.join(sessionPath, 'Default', 'Cookies-journal');
                    if (fs.existsSync(cookiesPath)) {
                        try {
                            fs.unlinkSync(cookiesPath);
                        } catch (err) {
                            console.log(`Não foi possível remover ${cookiesPath}: ${err.message}`);
                        }
                    }
                }
            });
        } catch (err) {
            console.log('Erro ao limpar sessões antigas:', err.message);
        }
    }
}

// Limpa sessões antigas na inicialização
cleanupOldSessions();

// --- GERENCIADOR DE CLIENTES ---
// Este objeto irá guardar todas as instâncias de clientes do WhatsApp,
// usando o ID da academia como chave. Ex: clients['1'] = cliente_da_academia_1
const clients = {};

/**
 * Cria e inicializa uma nova sessão de cliente do WhatsApp para uma academia específica.
 * @param {string} academiaId - O ID da academia do nosso banco de dados Django.
 */
function createClientSession(academiaId) {
    console.log(`Iniciando nova sessão para a academia ID: ${academiaId}`);

    // Usamos o 'clientId' para criar uma pasta de sessão separada para cada academia.
    // Ex: .wwebjs_auth/session-1, .wwebjs_auth/session-2, etc.
    const client = new Client({
        authStrategy: new LocalAuth({ 
            clientId: academiaId,
            dataPath: path.join(__dirname, '.wwebjs_auth')
        }),
        puppeteer: {
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-features=TranslateUI',
                '--disable-ipc-flooding-protection'
            ],
            headless: true,
            timeout: 60000,
            protocolTimeout: 60000
        }
    });

    // Armazenamos o cliente no nosso gerenciador
    clients[academiaId] = {
        instance: client,
        status: 'initializing',
        qrCode: null
    };

    client.on('qr', (qr) => {
        console.log(`QR Code gerado para a academia ID: ${academiaId}`);
        // Converte o QR code para um formato de imagem (data URL) que o navegador pode exibir
        qrcode.toDataURL(qr, (err, url) => {
            if (!err) {
                clients[academiaId].status = 'qr_ready';
                clients[academiaId].qrCode = url; // Armazena a imagem do QR code
            }
        });
    });

    client.on('ready', () => {
        console.log(`✔ Cliente para a academia ID: ${academiaId} está pronto!`);
        clients[academiaId].status = 'ready';
        clients[academiaId].qrCode = null; // Limpa o QR code após a conexão
    });

    client.on('disconnected', (reason) => {
        console.log(`Cliente para a academia ID: ${academiaId} foi desconectado. Motivo: ${reason}`);
        // Remove a sessão para forçar uma nova autenticação
        delete clients[academiaId];
    });

    client.on('auth_failure', (msg) => {
        console.log(`Falha na autenticação para academia ${academiaId}: ${msg}`);
        clients[academiaId].status = 'auth_failed';
    });

    client.initialize().catch(err => {
        console.error(`Falha ao inicializar cliente para academia ${academiaId}:`, err);
        clients[academiaId].status = 'error';
    });
}

// --- NOVOS ENDPOINTS DA API ---

// Endpoint para o Django pedir para iniciar uma sessão
app.post('/initialize', (req, res) => {
    const { academiaId } = req.body;
    if (!academiaId) {
        return res.status(400).json({ error: 'academiaId é obrigatório.' });
    }
    
    // Se já existe um cliente, tenta destruí-lo primeiro
    if (clients[academiaId]) {
        try {
            clients[academiaId].instance.destroy();
        } catch (err) {
            console.log('Erro ao destruir cliente existente:', err.message);
        }
        delete clients[academiaId];
    }
    
    createClientSession(academiaId);
    res.status(200).json({ message: 'Processo de inicialização iniciado.' });
});

// Endpoint para o frontend buscar o status da conexão
app.get('/status/:academiaId', (req, res) => {
    const { academiaId } = req.params;
    const session = clients[academiaId];
    if (session) {
        res.status(200).json({ status: session.status, qrCode: session.qrCode });
    } else {
        res.status(200).json({ status: 'disconnected' });
    }
});

// Endpoint para enviar mensagens (agora precisa saber de qual academia)
app.post('/send-message', async (req, res) => {
    const { academiaId, number, message } = req.body;
    const session = clients[academiaId];

    if (!session || session.status !== 'ready') {
        return res.status(400).json({ success: false, error: 'Cliente WhatsApp não está pronto ou conectado.' });
    }

    try {
        const formattedNumber = `${number.replace('+', '')}@c.us`;
        await session.instance.sendMessage(formattedNumber, message);
        res.status(200).json({ success: true, message: 'Mensagem enviada.' });
    } catch (error) {
        console.error(`Erro ao enviar mensagem pela academia ${academiaId}:`, error);
        res.status(500).json({ success: false, error: 'Falha ao enviar a mensagem.' });
    }
});

// Endpoint para desconectar uma sessão
app.post('/disconnect/:academiaId', (req, res) => {
    const { academiaId } = req.params;
    const session = clients[academiaId];
    
    if (session) {
        try {
            session.instance.destroy();
            delete clients[academiaId];
            res.status(200).json({ message: 'Sessão desconectada com sucesso.' });
        } catch (error) {
            console.error(`Erro ao desconectar sessão da academia ${academiaId}:`, error);
            res.status(500).json({ error: 'Falha ao desconectar a sessão.' });
        }
    } else {
        res.status(404).json({ error: 'Sessão não encontrada.' });
    }
});

// --- INICIANDO O SERVIDOR ---
app.listen(port, () => {
    console.log(`Gateway Multi-Tenant do WhatsApp rodando em http://localhost:${port}`);
});