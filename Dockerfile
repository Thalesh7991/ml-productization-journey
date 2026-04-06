# 1. Ponto de partida: Python 3.11 versão enxuta (slim = menor tamanho)
FROM python:3.11-slim

# 2. Define /app como pasta de trabalho dentro do container
WORKDIR /app

# 3. Copia o arquivo de dependências para dentro do container
COPY requirements.txt .

# 4. Instala as dependências listadas no requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copia o restante do projeto para dentro do container
COPY . .

# 6. Expõe a porta 8000 para acesso externo (caso seja necessário para a API)
EXPOSE 8000

# 7. Comando que roda quando o container inicia
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]