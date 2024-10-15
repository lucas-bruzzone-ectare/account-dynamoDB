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
        'status': 'ativo'
    }
    table.put_item(Item=item)
    return id_conta

def inserir_transacao(id_conta, valor, tipo, descricao):
    """
    Insere uma nova transação (crédito/débito) e atualiza o saldo.
    """
    timestamp = datetime.now().isoformat()
    transacao = {
        'PK': f'CONTA#{id_conta}',
        'SK': f'TRANS#{timestamp}',
        'valor': Decimal(str(valor)),
        'tipo': tipo,
        'descricao': descricao,
        'GSI1PK': f'CONTA#{id_conta}',
        'GSI1SK': f'TIPO#{tipo}'
    }
    
    # Atualizar saldo
    response = table.update_item(
        Key={'PK': f'CONTA#{id_conta}', 'SK': 'METADATA'},
        UpdateExpression='SET saldo_atual = saldo_atual + :val',
        ExpressionAttributeValues={':val': Decimal(str(valor)) if tipo == 'credito' else Decimal(str(-valor))},
        ReturnValues='UPDATED_NEW'
    )
    
    # Inserir transação
    table.put_item(Item=transacao)
    
    return response['Attributes']['saldo_atual']

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

def transferir_entre_contas(id_conta_origem, id_conta_destino, valor, descricao):
    """
    Realiza uma transferência entre duas contas.
    """
    try:
        dynamodb_client = boto3.client('dynamodb', region_name='us-west-2')

        # Prepare the transaction statements
        transaction_statements = [
            {
                'Statement': f"UPDATE ContasCorrente SET saldo_atual = saldo_atual - :val WHERE PK = :pk AND SK = :sk",
                'Parameters': [
                    {'N': str(valor)},
                    {'S': f'CONTA#{id_conta_origem}'},
                    {'S': 'METADATA'}
                ]
            },
            {
                'Statement': f"UPDATE ContasCorrente SET saldo_atual = saldo_atual + :val WHERE PK = :pk AND SK = :sk",
                'Parameters': [
                    {'N': str(valor)},
                    {'S': f'CONTA#{id_conta_destino}'},
                    {'S': 'METADATA'}
                ]
            }
        ]
        
        # Execute the transaction
        dynamodb_client.execute_transaction(TransactStatements=transaction_statements)

        # Registrar transações
        timestamp = datetime.now().isoformat()
        
        # Create the debit transaction for the origin account
        dynamodb_client.put_item(
            TableName='ContasCorrente',
            Item={
                'PK': {'S': f'CONTA#{id_conta_origem}'},
                'SK': {'S': f'TRANS#{timestamp}'},
                'tipo': {'S': 'debito'},
                'valor': {'N': str(valor)},
                'descricao': {'S': f'Transferência para conta {id_conta_destino}: {descricao}'},
                'GSI1PK': {'S': f'CONTA#{id_conta_origem}'},
                'GSI1SK': {'S': 'TIPO#debito'}
            }
        )

        # Create the credit transaction for the destination account
        dynamodb_client.put_item(
            TableName='ContasCorrente',
            Item={
                'PK': {'S': f'CONTA#{id_conta_destino}'},
                'SK': {'S': f'TRANS#{timestamp}'},
                'tipo': {'S': 'credito'},
                'valor': {'N': str(valor)},
                'descricao': {'S': f'Transferência de conta {id_conta_origem}: {descricao}'},
                'GSI1PK': {'S': f'CONTA#{id_conta_destino}'},
                'GSI1SK': {'S': 'TIPO#credito'}
            }
        )

        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'TransactionCanceledException':
            print("Saldo insuficiente para realizar a transferência.")
        else:
            print(f"Erro na transferência: {e}")
        return False




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
    
    try:
        # Atualizar saldo
        response = table.update_item(
            Key={'PK': f'CONTA#{id_conta}', 'SK': 'METADATA'},
            UpdateExpression='SET saldo_atual = saldo_atual + :val',
            ExpressionAttributeValues={':val': valor_reversao if tipo_reversao == 'credito' else -valor_reversao},
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
            'GSI1SK': f'TIPO#{tipo_reversao}'
        })
        
        return True, f"Transação revertida. Novo saldo: {response['Attributes']['saldo_atual']}"
    except Exception as e:
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

    # 1. Criar contas
    id_conta1 = criar_conta("Alice", 1000)
    id_conta2 = criar_conta("Bob", 500)
    print(f"Conta 1 (Alice) criada com ID: {id_conta1}")
    print(f"Conta 2 (Bob) criada com ID: {id_conta2}")

    # 2. Consultar saldos iniciais
    print(f"\nSaldo inicial Alice: R$ {consultar_saldo(id_conta1)}")
    print(f"Saldo inicial Bob: R$ {consultar_saldo(id_conta2)}")

    # 3. Inserir transações
    print("\nRealizando transações...")
    inserir_transacao(id_conta1, 200, "credito", "Depósito")
    inserir_transacao(id_conta1, 50, "debito", "Compra")
    inserir_transacao(id_conta2, 100, "credito", "Recebimento")

    # 4. Transferência entre contas
    print("\nRealizando transferência de Alice para Bob...")
    sucesso = transferir_entre_contas(id_conta1, id_conta2, 300, "Pagamento de aluguel")
    if sucesso:
        print("Transferência realizada com sucesso")
    else:
        print("Falha na transferência")

    # 5. Consultar saldos após transações
    print(f"\nNovo saldo Alice: R$ {consultar_saldo(id_conta1)}")
    print(f"Novo saldo Bob: R$ {consultar_saldo(id_conta2)}")

    # 6. Buscar histórico paginado
    print("\nHistórico de transações de Alice (paginado):")
    transacoes, last_key = buscar_historico_paginado(id_conta1)
    for t in transacoes:
        print(f"  {t['SK']} - Tipo: {t['tipo']}, Valor: R$ {t['valor']}, Descrição: {t['descricao']}")

    # 7. Reverter uma transação
    if transacoes:
        print("\nRevertendo a última transação de Alice...")
        sucesso, mensagem = reverter_transacao(id_conta1, transacoes[0]['SK'])
        print(mensagem)

    # 8. Verificar saldo disponível
    valor_verificacao = 800
    disponivel = verificar_saldo_disponivel(id_conta1, valor_verificacao)
    print(f"\nSaldo disponível para transação de R$ {valor_verificacao} na conta de Alice: {'Sim' if disponivel else 'Não'}")

    # 9. Gerar relatório simples
    print("\nRelatório simples da conta de Alice (últimos 7 dias):")
    relatorio = gerar_relatorio_simples(id_conta1, 7)
    for key, value in relatorio.items():
        print(f"  {key}: {value}")

    # 10. Consultar saldos finais
    print(f"\nSaldo final Alice: R$ {consultar_saldo(id_conta1)}")
    print(f"Saldo final Bob: R$ {consultar_saldo(id_conta2)}")