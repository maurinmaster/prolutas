# Gateway WhatsApp Multi-Tenant

Este é o gateway do WhatsApp para o sistema ProLutas, responsável por gerenciar múltiplas sessões do WhatsApp Web para diferentes academias.

## 🚀 Como usar

### 1. Instalar dependências
```bash
npm install
```

### 2. Limpar sessões antigas (se necessário)
Se você encontrar erros de arquivos bloqueados, execute:
```bash
npm run cleanup
```

### 3. Iniciar o gateway
```bash
npm start
```

### 4. Para desenvolvimento (com auto-reload)
```bash
npm run dev
```

## 🔧 Endpoints da API

### Inicializar sessão
```http
POST /initialize
Content-Type: application/json

{
  "academiaId": "1"
}
```

### Verificar status
```http
GET /status/:academiaId
```

### Enviar mensagem
```http
POST /send-message
Content-Type: application/json

{
  "academiaId": "1",
  "number": "5511999999999",
  "message": "Olá! Esta é uma mensagem automática."
}
```

### Desconectar sessão
```http
POST /disconnect/:academiaId
```

## 🔍 Solução de Problemas

### Erro EBUSY (arquivo bloqueado)
Este erro é comum no Windows. Para resolver:

1. **Pare o gateway** (Ctrl+C)
2. **Execute a limpeza:**
   ```bash
   npm run cleanup
   ```
3. **Reinicie o gateway:**
   ```bash
   npm start
   ```

### QR Code não aparece
1. Verifique se o gateway está rodando na porta 3000
2. Acesse `http://localhost:3000/status/1` para verificar o status
3. Se necessário, reinicialize a sessão

### Mensagens não são enviadas
1. Verifique se o status da sessão é "ready"
2. Certifique-se de que o número está no formato correto (apenas números)
3. Verifique se o WhatsApp Web está conectado no navegador

## 📁 Estrutura de Arquivos

```
whatsapp_gateway/
├── index.js          # Servidor principal
├── cleanup.js        # Script de limpeza
├── package.json      # Dependências
├── README.md         # Este arquivo
└── .wwebjs_auth/     # Sessões (criado automaticamente)
```

## 🔒 Segurança

- O gateway roda apenas em localhost (127.0.0.1)
- Cada academia tem sua própria sessão isolada
- As sessões são armazenadas localmente

## 🐛 Logs

O gateway gera logs detalhados no console. Monitore para:
- Status de conexão
- Erros de autenticação
- Problemas de envio de mensagens
- Limpeza de sessões

## 📞 Suporte

Se encontrar problemas:
1. Execute `npm run cleanup`
2. Reinicie o gateway
3. Verifique os logs no console
4. Certifique-se de que o WhatsApp Web está funcionando
