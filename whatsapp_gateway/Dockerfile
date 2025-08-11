# Usa uma imagem oficial do Node.js
FROM node:18

# Define o diretório de trabalho
WORKDIR /usr/src/app

# Copia os arquivos de dependência
COPY whatsapp_gateway/package*.json ./

# Instala as dependências
RUN npm install

# Copia o resto do código
COPY whatsapp_gateway/ .

# Expõe a porta que o serviço vai usar
EXPOSE 3000

# Comando para iniciar o serviço
CMD [ "node", "index.js" ]