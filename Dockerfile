# Usa uma imagem oficial do Python como base
FROM python:3.12-slim

# Define variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Cria e define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Instala as dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia o arquivo de requerimentos e instala as dependências do Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código do projeto para dentro do contêiner
COPY . .

# Expõe a porta que o Gunicorn vai usar
EXPOSE 8000