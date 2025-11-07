# Imagem base leve com Python 3.12
FROM python:3.12-slim

# Define diretório de trabalho dentro do container
WORKDIR /app

# Copia o requirements.txt e instala dependências
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copia o restante do projeto para dentro do container
COPY . .

# Garante que o arquivo placas.csv exista (evita erro IsADirectoryError)
RUN touch /app/placas.csv

# Exponha a porta usada pelo FastAPI (8000)
EXPOSE 8000

# Comando padrão para rodar o servidor Uvicorn (sem reload em produção)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
