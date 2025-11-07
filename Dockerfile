# Imagem base leve com Python 3.12
FROM python:3.12-slim

# Define o diretório de trabalho
WORKDIR /app

# Copia apenas dependências primeiro
COPY requirements.txt .

# Instala dependências do projeto
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copia o restante do código-fonte (sem CSV)
COPY . .

# Garante que a pasta static e templates existam
RUN mkdir -p /app/static /app/templates

# Expõe a porta usada pelo FastAPI
EXPOSE 8000

# Comando padrão de execução
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
