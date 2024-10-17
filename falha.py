import boto3
from botocore.exceptions import ClientError
from decimal import Decimal
import threading
import time
import random

# Configuração do DynamoDB
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('ContasCorrente')

def simular_transacao_concorrente(id_conta, valor, tentativas=5):
    for tentativa in range(tentativas):
        try:
            # Obter a versão atual e o saldo
            response = table.get_item(Key={"PK": id_conta, "SK": "METADATA"})
            if "Item" not in response:
                raise ValueError("Conta não encontrada.")

            version = response["Item"]["version"]
            saldo_atual = Decimal(response["Item"]["saldo_atual"])

            # Verificar se o saldo não ficará negativo (pode remover esta lógica se não precisar)
            if saldo_atual + Decimal(valor) < 0:
                print(f"Saldo insuficiente na conta {id_conta}. Saldo atual: {saldo_atual}")
                return

            # Tentar atualizar o saldo
            dynamodb.meta.client.transact_write_items(
                TransactItems=[
                    {
                        "Update": {
                            "TableName": table.name,
                            "Key": {"PK": id_conta, "SK": "METADATA"},
                            "UpdateExpression": "SET saldo_atual = saldo_atual + :val, version = :new_version",
                            "ExpressionAttributeValues": {
                                ":val": Decimal(str(valor)),
                                ":new_version": version + 1,
                                ":current_version": version,
                            },
                            "ConditionExpression": "version = :current_version",
                        }
                    }
                ]
            )
            print(f"Transação bem-sucedida: {threading.current_thread().name}")
            return  # Sucesso, sai da função

        except ClientError as e:
            if e.response['Error']['Code'] == 'TransactionCanceledException':
                print(f"Transação falhou (conflito de concorrência): {threading.current_thread().name}, tentativa {tentativa + 1}")
            else:
                print(f"Erro na transação: {e}")
                return  # Erro não relacionado à concorrência
        time.sleep(random.uniform(0.1, 0.5))  # Espera antes de tentar novamente
    print(f"Transação falhou após {tentativas} tentativas: {threading.current_thread().name}")

def main():
    id_conta = "CONTA#54697cf7-11a8-4747-9537-7ad02f6a261f"  # ID da conta de exemplo
    
    # Criar várias threads para simular transações concorrentes em diferentes contas
    threads = []
    for i in range(10):
        valor = random.choice([100, -50, 200, -150])  # Valores variados, incluindo débito/crédito
        atraso = random.uniform(0, 0.2)  # Atraso aleatório
        thread = threading.Thread(target=simular_transacao_concorrente, args=(id_conta, valor), name=f"Thread-{i+1}")
        threads.append(thread)
        thread.start()

    # Aguardar todas as threads terminarem
    for thread in threads:
        thread.join()

    # Verificar o resultado final
    response = table.get_item(Key={"PK": id_conta, "SK": "METADATA"})
    if "Item" in response:
        print(f"Saldo final: {response['Item']['saldo_atual']}")
    else:
        print("Não foi possível recuperar o saldo final.")

if __name__ == "__main__":
    main()
