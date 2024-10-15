import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal
import uuid
from datetime import datetime, timedelta
from botocore.exceptions import ClientError

# Inicializar o cliente DynamoDB
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('ContasCorrente')

def criar_conta(nome_titular, saldo_inicial):
    """
    Cria uma nova conta com saldo inicial.
    """
    id_conta = str(uuid.uuid4())
    item = {
        'PK': f'CONTA#{id_conta}',
        'SK': 'METADATA',
        'nome_titular': nome_titular,
        'saldo_atual': Decimal(str(saldo_inicial)),
        'status': 'ativo',
        'version': 1  # Inicializa a versão
    }
    table.put_item(Item=item)
    return id_conta

def inserir_transacao(id_conta, valor, tipo, descricao):
    """
    Insere uma nova transação (crédito/débito) e atualiza o saldo.
    """
    timestamp = datetime.now().isoformat()
    
    # Obter a versão atual
    response = table.get_item(Key={'PK': f'CONTA#{id_conta}', 'SK': 'METADATA'})
    version = response['Item']['version']
    
    transacao = {
        'PK': f'CONTA#{id_conta}',
        'SK': f'TRANS#{timestamp}',
        'valor': Decimal(str(valor)),
        'tipo': tipo,
        'descricao': descricao,
        'GSI1PK': f'CONTA#{id_conta}',
        'GSI1SK': f'TIPO#{tipo}'
    }

    # Atualizar saldo com controle de versão
    try:
        response = table.update_item(
            Key={'PK': f'CONTA#{id_conta}', 'SK': 'METADATA'},
            UpdateExpression='SET saldo_atual = saldo_atual + :val, version = version + :inc',
            ExpressionAttributeValues={
                ':val': Decimal(str(valor)) if tipo == 'credito' else Decimal(str(-valor)),
                ':inc': 1,  # Incrementa a versão
                ':current_version': version  # Verifica a versão atual
            },
            ConditionExpression='version = :current_version',  # Condição para verificar a versão
            ReturnValues='UPDATED_NEW'
        )
        
        # Inserir transação
        table.put_item(Item=transacao)
        
        return response['Attributes']['saldo_atual']
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            raise Exception("Conflito de concorrência: outra operação atualizou a conta antes desta transação.")
        else:
            raise

def consultar_saldo(id_conta):
    """
    Consulta o saldo atual da conta.
    """
    response = table.get_item(
        Key={'PK': f'CONTA#{id_conta}', 'SK': 'METADATA'}
    )
    return response['Item']['saldo_atual']

def buscar_historico_transacoes(id_conta, limit=10):
    """
    Busca o histórico de transações por conta.
    """
    response = table.query(
        KeyConditionExpression=Key('PK').eq(f'CONTA#{id_conta}') & Key('SK').begins_with('TRANS#'),
        ScanIndexForward=False,  # ordem decrescente (mais recente primeiro)
        Limit=limit
    )
    return response['Items']

def verificar_saldo_disponivel(id_conta, valor):
    """
    Verifica se há saldo disponível para uma transação.
    """
    saldo_atual = consultar_saldo(id_conta)
    return saldo_atual >= Decimal(str(valor))

def buscar_historico_paginado(id_conta, limit=5, last_evaluated_key=None):
    """
    Busca o histórico de transações com paginação.
    """
    params = {
        'KeyConditionExpression': Key('PK').eq(f'CONTA#{id_conta}') & Key('SK').begins_with('TRANS#'),
        'ScanIndexForward': False,
        'Limit': limit
    }
    if last_evaluated_key:
        params['ExclusiveStartKey'] = last_evaluated_key
    
    response = table.query(**params)
    return response.get('Items', []), response.get('LastEvaluatedKey')

def reverter_transacao(id_conta, sk_transacao):
    """
    Reverte uma transação específica.
    """
    # Buscar a transação original
    response = table.get_item(Key={'PK': f'CONTA#{id_conta}', 'SK': sk_transacao})
    if 'Item' not in response:
        return False, "Transação não encontrada"
    
    transacao_original = response['Item']
    valor_original = transacao_original['valor']
    tipo_original = transacao_original['tipo']
    
    # Calcular o valor e tipo da reversão
    valor_reversao = valor_original
    tipo_reversao = 'credito' if tipo_original == 'debito' else 'debito'
    
    # Obter a versão atual
    response = table.get_item(Key={'PK': f'CONTA#{id_conta}', 'SK': 'METADATA'})
    version = response['Item']['version']
    
    try:
        # Atualizar saldo com controle de versão
        response = table.update_item(
            Key={'PK': f'CONTA#{id_conta}', 'SK': 'METADATA'},
            UpdateExpression='SET saldo_atual = saldo_atual + :val, version = version + :inc',
            ExpressionAttributeValues={
                ':val': valor_reversao if tipo_reversao == 'credito' else -valor_reversao,
                ':inc': 1,  # Incrementa a versão
                ':current_version': version  # Verifica a versão atual
            },
            ConditionExpression='version = :current_version',  # Condição para verificar a versão
            ReturnValues='UPDATED_NEW'
        )
        
        # Registrar transação de reversão
        timestamp = datetime.now().isoformat()
        table.put_item(Item={
            'PK': f'CONTA#{id_conta}',
            'SK': f'TRANS#{timestamp}',
            'tipo': tipo_reversao,
            'valor': valor_reversao,
            'descricao': f'Reversão de transação: {sk_transacao}',
            'GSI1PK': f'CONTA#{id_conta}',
            'GSI1SK': f'TIPO#{tipo_reversao}',
            'version': version + 1  # Atualiza a versão
        })
        
        return True, f"Transação revertida. Novo saldo: {response['Attributes']['saldo_atual']}"
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return False, "Conflito de concorrência: outra operação atualizou a conta antes da reversão."
        else:
            return False, str(e)

def consultar_transacoes_por_periodo(id_conta, data_inicio, data_fim):
    """
    Consulta transações por período específico.
    """
    response = table.query(
        KeyConditionExpression=Key('PK').eq(f'CONTA#{id_conta}') & 
                               Key('SK').between(f'TRANS#{data_inicio.isoformat()}', f'TRANS#{data_fim.isoformat()}'),
        ScanIndexForward=True  # ordem crescente de data
    )
    return response['Items']

def gerar_relatorio_simples(id_conta, periodo_dias=30):
    """
    Gera um relatório simples com agregações básicas.
    """
    data_fim = datetime.now()
    data_inicio = data_fim - timedelta(days=periodo_dias)
    
    transacoes = consultar_transacoes_por_periodo(id_conta, data_inicio, data_fim)
    
    total_creditos = sum(float(t['valor']) for t in transacoes if t['tipo'] == 'credito')
    total_debitos = sum(float(t['valor']) for t in transacoes if t['tipo'] == 'debito')
    saldo_periodo = total_creditos - total_debitos
    
    return {
        'periodo': f'{data_inicio.date()} a {data_fim.date()}',
        'total_transacoes': len(transacoes),
        'total_creditos': total_creditos,
        'total_debitos': total_debitos,
        'saldo_periodo': saldo_periodo
    }

# Demonstração de todos os cenários
if __name__ == "__main__":
    print("Demonstração da POC de Conta Corrente com DynamoDB\n")

    # Criar uma conta
    id_conta = criar_conta("João Silva", 1000)
    print(f"Conta criada com ID: {id_conta}")

    # Inserir transações
    try:
        inserir_transacao(id_conta, 200, 'credito', 'Depósito inicial')
        print(f"Saldo após depósito: {consultar_saldo(id_conta)}")

        inserir_transacao(id_conta, 150, 'debito', 'Pagamento de conta')
        print(f"Saldo após pagamento: {consultar_saldo(id_conta)}")

    except Exception as e:
        print(f"Erro: {e}")

    # Buscar histórico
    transacoes = buscar_historico_transacoes(id_conta)
    print(f"Histórico de transações: {transacoes}")

    # Reverter transação
    try:
        resultado_reversao = reverter_transacao(id_conta, transacoes[0]['SK'])
        print(resultado_reversao)
        print(f"Saldo após reversão: {consultar_saldo(id_conta)}")
    except Exception as e:
        print(f"Erro ao reverter transação: {e}")

    # Gerar relatório
    relatorio = gerar_relatorio_simples(id_conta, periodo_dias=30)
    print(f"Relatório Simples: {relatorio}")
