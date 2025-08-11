// whatsapp_gateway/cleanup.js
const fs = require('fs');
const path = require('path');

console.log('🧹 Iniciando limpeza das sessões do WhatsApp Web.js...');

const authDir = path.join(__dirname, '.wwebjs_auth');

if (fs.existsSync(authDir)) {
    try {
        // Remove todo o diretório de autenticação
        fs.rmSync(authDir, { recursive: true, force: true });
        console.log('✅ Diretório .wwebjs_auth removido com sucesso!');
    } catch (err) {
        console.error('❌ Erro ao remover diretório:', err.message);
        
        // Se não conseguir remover tudo, tenta remover arquivos específicos
        try {
            const sessions = fs.readdirSync(authDir);
            sessions.forEach(session => {
                const sessionPath = path.join(authDir, session);
                if (fs.statSync(sessionPath).isDirectory()) {
                    const defaultPath = path.join(sessionPath, 'Default');
                    if (fs.existsSync(defaultPath)) {
                        const files = fs.readdirSync(defaultPath);
                        files.forEach(file => {
                            if (file.includes('Cookies') || file.includes('Session')) {
                                try {
                                    fs.unlinkSync(path.join(defaultPath, file));
                                    console.log(`✅ Removido: ${file}`);
                                } catch (err) {
                                    console.log(`⚠️ Não foi possível remover ${file}: ${err.message}`);
                                }
                            }
                        });
                    }
                }
            });
        } catch (err2) {
            console.error('❌ Erro ao limpar arquivos específicos:', err2.message);
        }
    }
} else {
    console.log('ℹ️ Diretório .wwebjs_auth não encontrado.');
}

console.log('🎯 Limpeza concluída! Agora você pode reiniciar o gateway do WhatsApp.');
