# Usa uma imagem oficial do Node.js
FROM node:18

# Define o diretório de trabalho
WORKDIR /usr/src/app

# Instala as dependências de sistema necessárias para o Puppeteer (usado pelo whatsapp-web.js)
RUN apt-get update && apt-get install -yq --no-install-recommends \
    gconf-service libasound2 libatk1.0-0 libc6 libcairo2 libcups2 libdbus-1-3 \
    libexpat1 libfontconfig1 libgcc1 libgconf-2-4 libgdk-pixbuf2.0-0 libglib2.0-0 libgtk-3-0 libnspr4 \
    libpango-1.0-0 libpangocairo-1.0-0 libstdc++6 libx11-6 libx11-xcb1 libxcb1 \
    libxcomposite1 libxcursor1 libxdamage1 libxext6 libxfixes3 libxi6 libxrandr2 \
    libxrender1 libxss1 libxtst6 ca-certificates fonts-liberation libappindicator1 libnss3 \
    lsb-release xdg-utils wget \
    && rm -rf /var/lib/apt/lists/*

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