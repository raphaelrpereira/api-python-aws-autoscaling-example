from flask import Flask, request
from flasgger import Swagger
import boto3
import datetime
import requests

# --- CONFIGURAÇÃO INICIAL ---
BUCKET_NAME = "SEU-NOME-DE-BUCKET-AQUI" 

app = Flask(__name__)
swagger = Swagger(app)
s3_client = boto3.client('s3')

# --- NOVA FUNÇÃO ---
# Função para obter o ID da instância EC2 a partir do serviço de metadados
def get_instance_id():
    try:
        # A URL para o Instance ID é diferente da do IP. Usamos o endereço correto.
        response = requests.get('http://169.254.169.254/latest/meta-data/instance-id', timeout=2)
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Nao foi possivel obter o ID da instancia: {e}")
        return "ID-nao-disponivel"

# --- ROTA HEALTH CHECK MODIFICADA ---
@app.route('/', methods=['GET'])
def health_check():
    """
    Verifica a saúde da API e o balanceamento de carga.
    Retorna uma página HTML que exibe o ID da instância do servidor que processou a requisição.
    ---
    responses:
      200:
        description: A API está funcionando corretamente.
    """
    instance_id = get_instance_id()
    return f"""
    <html>
        <head><title>Health Check</title></head>
        <body style='font-family: sans-serif; text-align: center; padding-top: 50px;'>
            <h1>API esta no ar!</h1>
            <p>Esta requisicao foi processada pelo servidor: <strong>{instance_id}</strong></p>
            <p>Atualize a pagina (F5) para ver o Load Balancer em acao!</p>
        </body>
    </html>
    """, 200

# --- ROTA DE DADOS MODIFICADA ---
@app.route('/dados', methods=['POST'])
def salvar_dados():
    """
    Recebe dados brutos e os salva em um arquivo no S3.
    O nome do arquivo e seu conteúdo incluirão o ID da instância que o processou.
    ---
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: string
          example: "Meus dados de teste para a aula de nuvem."
    responses:
      201: {description: Dados salvos com sucesso no S3.}
      400: {description: Erro - o corpo da requisição estava vazio.}
      500: {description: Erro interno ao tentar salvar no S3.}
    """
    dados_recebidos = request.data
    if not dados_recebidos:
        return "Corpo da requisicao esta vazio.", 400

    instance_id = get_instance_id()
    timestamp = datetime.datetime.now().strftime("%Y-m-d-%H-%M-%S-%f")
    # O nome do arquivo agora usa o Instance ID
    file_name = f"servidor-{instance_id}-dado-{timestamp}.txt"
    # O conteúdo do arquivo também registra o Instance ID
    conteudo_para_salvar = f"Processado pelo servidor: {instance_id}\n---\n".encode('utf-8') + dados_recebidos

    try:
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=file_name,
            Body=conteudo_para_salvar
        )
        return f"Dados salvos com sucesso no arquivo {file_name} pelo servidor {instance_id}", 201
    except Exception as e:
        print(e)
        return f"Erro ao salvar no S3: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
