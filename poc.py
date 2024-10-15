import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal
import uuid
from datetime import datetime
from botocore.exceptions import ClientError


# Inicializar o cliente DynamoDB
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('ContasCorrente')



def criar_conta(nome_titular, saldo_inicial):
    """
    Cria uma nova conta com saldo inicial.
    
    Args:
        nome_titular (str): Nome do titular da conta.
        saldo_inicial (float): Saldo inicial da conta.

    Returns:
        str: ID da conta criada.
    """
    if not isinstance(nome_titular, str) or not nome_titular.strip():
        raise ValueError("O nome do titular deve ser uma string válida.")
    if not isinstance(saldo_inicial, (int, float)) or saldo_inicial < 0:
        raise ValueError("O saldo inicial deve ser um número não negativo.")

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

    Args:
        id_conta (str): ID da conta.
        valor (float): Valor da transação.
        tipo (str): Tipo da transação ('credito' ou 'debito').
        descricao (str): Descrição da transação.

    Returns:
        Decimal: Novo saldo após a transação.
    """
    if tipo not in ['credito', 'debito']:
        raise ValueError("O tipo da transação deve ser 'credito' ou 'debito'.")
    if not isinstance(valor, (int, float)) or valor <= 0:
        raise ValueError("O valor da transação deve ser um número positivo.")

    timestamp = datetime.now().isoformat()
    
    # Obter a versão atual
    response = table.get_item(Key={'PK': f'CONTA#{id_conta}', 'SK': 'METADATA'})
    version = response['Item']['version']
    
    # Verificar saldo disponível se for uma operação de débito
    if tipo == 'debito':
        saldo_atual = response['Item']['saldo_atual']
        if saldo_atual < Decimal(str(valor)):
            raise ValueError("Saldo insuficiente para a operação.")

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

    Args:
        id_conta (str): ID da conta.

    Returns:
        Decimal: Saldo atual da conta.
    """
    response = table.get_item(
        Key={'PK': f'CONTA#{id_conta}', 'SK': 'METADATA'}
    )
    saldo = response['Item']['saldo_atual']
    return saldo

def buscar_historico_transacoes(id_conta, limit=10):
    """
    Busca o histórico de transações por conta.

    Args:
        id_conta (str): ID da conta.
        limit (int): Limite de transações a serem retornadas.

    Returns:
        list: Lista de transações.
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

    Args:
        id_conta (str): ID da conta.
        valor (float): Valor a ser verificado.

    Returns:
        bool: True se houver saldo disponível, False caso contrário.
    """
    saldo_atual = consultar_saldo(id_conta)
    return saldo_atual >= Decimal(str(valor))

def buscar_historico_paginado(id_conta, limit=5, last_evaluated_key=None):
    """
    Busca o histórico de transações com paginação.

    Args:
        id_conta (str): ID da conta.
        limit (int): Limite de transações a serem retornadas.
        last_evaluated_key (dict): Chave de início para a paginação.

    Returns:
        tuple: Lista de transações e última chave avaliada.
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

    Args:
        id_conta (str): ID da conta.
        sk_transacao (str): Chave da transação a ser revertida.

    Returns:
        tuple: (bool, str) Status da reversão e mensagem.
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
            'valor': Decimal(str(valor_reversao)),
            'tipo': tipo_reversao,
            'descricao': f'Reversão de: {transacao_original["descricao"]}',
            'GSI1PK': f'CONTA#{id_conta}',
            'GSI1SK': f'TIPO#{tipo_reversao}'
        })
        
        return True, "Transação revertida com sucesso"
    except ClientError as e:
        return False, str(e)

def imprimir_saldo(saldo):
    """Imprime o saldo atual de forma formatada."""
    print(f"\n{'='*20}\nSaldo atual: R${saldo:.2f}\n{'='*20}")

def imprimir_historico(transacoes):
    """Imprime o histórico de transações de forma organizada."""
    print("\nHistórico de Transações:")
    print('-' * 30)
    for transacao in transacoes:
        print(f"{transacao['tipo'].capitalize()} | Valor: R${transacao['valor']:.2f} | Descrição: {transacao['descricao']} | Data: {transacao['SK'].replace('TRANS#', '')}")
    print('-' * 30)

def imprimir_resultado_reversao(mensagem):
    """Imprime o resultado da reversão da transação."""
    print("\nResultado da Reversão:")
    print(f"{mensagem}\n{'='*20}")

def imprimir_transacoes_paginadas(transacoes, last_key):
    """Imprime as transações paginadas de forma organizada."""
    print("\nTransações Paginadas:")
    print('-' * 30)
    for transacao in transacoes:
        print(f"{transacao['tipo'].capitalize()} | Valor: R${transacao['valor']:.2f} | Descrição: {transacao['descricao']} | Data: {transacao['SK'].replace('TRANS#', '')}")
    print('-' * 30)
    if last_key:
        print(f"Última chave avaliada: {last_key}\n{'='*20}")

# Exemplo de uso com impressão formatada
if __name__ == "__main__":
    # Criar uma conta
    id_conta = criar_conta("João Silva", 1000.00)


    inserir_transacao(id_conta, 200.00, 'credito', 'Depósito de salário')
    inserir_transacao(id_conta, 50.00, 'debito', 'Compra no supermercado')


    # Consultar saldo
    saldo = consultar_saldo(id_conta)
    imprimir_saldo(saldo)

    # Buscar histórico de transações
    transacoes = buscar_historico_transacoes(id_conta)
    imprimir_historico(transacoes)

    # Reverter uma transação
    if transacoes:
        sk_transacao = transacoes[0]['SK']
        status, mensagem = reverter_transacao(id_conta, sk_transacao)
        imprimir_resultado_reversao(mensagem)

    # Verificar saldo disponível
    saldo_disponivel = verificar_saldo_disponivel(id_conta, 50)
    print(f"Saldo disponível para transação: {'Sim' if saldo_disponivel else 'Não'}")

    # Buscar histórico paginado
    transacoes_paginadas, last_key = buscar_historico_paginado(id_conta, limit=2)
    imprimir_transacoes_paginadas(transacoes_paginadas, last_key)

