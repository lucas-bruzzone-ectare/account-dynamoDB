import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal, ROUND_HALF_UP
import uuid
from datetime import datetime
from botocore.exceptions import ClientError
import os
import logging
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.CRITICAL)
logger = logging.getLogger(__name__)

# Inicializar o cliente DynamoDB
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ.get("DYNAMODB_TABLE_NAME", "ContasCorrente"))


class TipoTransacao(Enum):
    CREDITO = "credito"
    DEBITO = "debito"


def criar_conta(nome_titular, saldo_inicial):
    """
    Cria uma nova conta com saldo inicial.
    """
    try:
        if not isinstance(nome_titular, str) or not nome_titular.strip():
            raise ValueError("O nome do titular deve ser uma string válida.")
        if not isinstance(saldo_inicial, (int, float)) or saldo_inicial < 0:
            raise ValueError("O saldo inicial deve ser um número não negativo.")

        id_conta = str(uuid.uuid4())
        item = {
            "PK": f"CONTA#{id_conta}",
            "SK": "METADATA",
            "nome_titular": nome_titular,
            "saldo_atual": Decimal(str(saldo_inicial)).quantize(
                Decimal(".01"), rounding=ROUND_HALF_UP
            ),
            "status": "ativo",
            "version": 1,
        }
        table.put_item(Item=item)
        logger.info(f"Conta criada com sucesso: {id_conta}")
        return id_conta
    except ClientError as e:
        logger.error(f"Erro ao criar conta: {e}")
        raise
    except Exception as e:
        logger.error(f"Erro inesperado ao criar conta: {e}")
        raise


def inserir_transacao(id_conta, valor, tipo, descricao):
    """
    Insere uma nova transação (crédito/débito) e atualiza o saldo.
    """
    try:
        if not isinstance(tipo, TipoTransacao):
            raise ValueError("O tipo da transação deve ser um TipoTransacao.")
        if not isinstance(valor, (int, float)) or valor <= 0:
            raise ValueError("O valor da transação deve ser um número positivo.")

        valor_decimal = Decimal(str(valor)).quantize(
            Decimal(".01"), rounding=ROUND_HALF_UP
        )
        timestamp = datetime.now().isoformat()

        # Obter a versão atual e o saldo
        response = table.get_item(Key={"PK": f"CONTA#{id_conta}", "SK": "METADATA"})
        if "Item" not in response:
            raise ValueError("Conta não encontrada.")

        version = response["Item"]["version"]
        saldo_atual = response["Item"]["saldo_atual"]

        # Verificar saldo disponível se for uma operação de débito
        if tipo == TipoTransacao.DEBITO and saldo_atual < valor_decimal:
            raise ValueError("Saldo insuficiente para a operação.")

        # Usar transação para garantir consistência
        dynamodb.meta.client.transact_write_items(
            TransactItems=[
                {
                    "Update": {
                        "TableName": table.name,
                        "Key": {"PK": f"CONTA#{id_conta}", "SK": "METADATA"},
                        "UpdateExpression": "SET saldo_atual = saldo_atual + :val, version = :new_version",
                        "ExpressionAttributeValues": {
                            ":val": (
                                valor_decimal
                                if tipo == TipoTransacao.CREDITO
                                else -valor_decimal
                            ),
                            ":new_version": version + 1,
                            ":current_version": version,
                        },
                        "ConditionExpression": "version = :current_version",
                    }
                },
                {
                    "Put": {
                        "TableName": table.name,
                        "Item": {
                            "PK": f"CONTA#{id_conta}",
                            "SK": f"TRANS#{timestamp}",
                            "valor": valor_decimal,
                            "tipo": tipo.value,
                            "descricao": descricao,
                            "GSI1PK": f"CONTA#{id_conta}",
                            "GSI1SK": f"TIPO#{tipo.value}",
                            "revertida": False,
                        },
                    }
                },
            ]
        )
        logger.info(
            f"Transação inserida com sucesso: {id_conta}, {tipo.value}, {valor_decimal}"
        )
        return consultar_saldo(id_conta)
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            logger.warning(f"Conflito de concorrência ao inserir transação: {id_conta}")
            raise ValueError("Conflito de concorrência: tente novamente.")
        logger.error(f"Erro ao inserir transação: {e}")
        raise
    except Exception as e:
        logger.error(f"Erro inesperado ao inserir transação: {e}")


def consultar_saldo(id_conta):
    """
    Consulta o saldo atual da conta.
    """
    try:
        response = table.get_item(Key={"PK": f"CONTA#{id_conta}", "SK": "METADATA"})
        if "Item" not in response:
            raise ValueError("Conta não encontrada.")
        saldo = response["Item"]["saldo_atual"]
        logger.info(f"Saldo consultado com sucesso: {id_conta}")
        return saldo
    except ClientError as e:
        logger.error(f"Erro ao consultar saldo: {e}")
        raise
    except Exception as e:
        logger.error(f"Erro inesperado ao consultar saldo: {e}")
        raise


def buscar_historico_transacoes(id_conta, limit=10):
    """
    Busca o histórico de transações por conta.
    """
    try:
        response = table.query(
            KeyConditionExpression=Key("PK").eq(f"CONTA#{id_conta}")
            & Key("SK").begins_with("TRANS#"),
            ScanIndexForward=False,  # ordem decrescente (mais recente primeiro)
            Limit=limit,
        )
        logger.info(f"Histórico de transações consultado com sucesso: {id_conta}")
        return response["Items"]
    except ClientError as e:
        logger.error(f"Erro ao buscar histórico de transações: {e}")
        raise
    except Exception as e:
        logger.error(f"Erro inesperado ao buscar histórico de transações: {e}")
        raise


def verificar_saldo_disponivel(id_conta, valor):
    """
    Verifica se há saldo disponível para uma transação.
    """
    try:
        saldo_atual = consultar_saldo(id_conta)
        saldo_disponivel = saldo_atual >= Decimal(str(valor))
        logger.info(f"Verificação de saldo disponível concluída: {id_conta}")
        return saldo_disponivel
    except Exception as e:
        logger.error(f"Erro ao verificar saldo disponível: {e}")
        raise


def buscar_historico_paginado(id_conta, limit=5, last_evaluated_key=None):
    """
    Busca o histórico de transações com paginação.
    """
    try:
        params = {
            "KeyConditionExpression": Key("PK").eq(f"CONTA#{id_conta}")
            & Key("SK").begins_with("TRANS#"),
            "ScanIndexForward": False,
            "Limit": limit,
        }
        if last_evaluated_key:
            params["ExclusiveStartKey"] = last_evaluated_key

        response = table.query(**params)
        logger.info(f"Histórico paginado consultado com sucesso: {id_conta}")
        return response.get("Items", []), response.get("LastEvaluatedKey")
    except ClientError as e:
        logger.error(f"Erro ao buscar histórico paginado: {e}")
        raise
    except Exception as e:
        logger.error(f"Erro inesperado ao buscar histórico paginado: {e}")
        raise


def reverter_transacao(id_conta, sk_transacao):
    """
    Reverte uma transação específica.
    """
    try:
        # Buscar a transação original
        response = table.get_item(Key={"PK": f"CONTA#{id_conta}", "SK": sk_transacao})
        if "Item" not in response:
            raise ValueError("Transação não encontrada")

        transacao_original = response["Item"]
        if transacao_original.get("revertida", False):
            raise ValueError("Esta transação já foi revertida")

        valor_original = transacao_original["valor"]
        tipo_original = transacao_original["tipo"]

        # Calcular o valor e tipo da reversão
        valor_reversao = valor_original
        tipo_reversao = (
            TipoTransacao.CREDITO
            if tipo_original == TipoTransacao.DEBITO.value
            else TipoTransacao.DEBITO
        )

        # Obter a versão atual
        response = table.get_item(Key={"PK": f"CONTA#{id_conta}", "SK": "METADATA"})
        if "Item" not in response:
            raise ValueError("Conta não encontrada")
        version = response["Item"]["version"]

        timestamp = datetime.now().isoformat()

        # Usar transação para garantir consistência
        dynamodb.meta.client.transact_write_items(
            TransactItems=[
                {
                    "Update": {
                        "TableName": table.name,
                        "Key": {"PK": f"CONTA#{id_conta}", "SK": "METADATA"},
                        "UpdateExpression": "SET saldo_atual = saldo_atual + :val, version = :new_version",
                        "ExpressionAttributeValues": {
                            ":val": (
                                valor_reversao
                                if tipo_reversao == TipoTransacao.CREDITO
                                else -valor_reversao
                            ),
                            ":new_version": version + 1,
                            ":current_version": version,
                        },
                        "ConditionExpression": "version = :current_version",
                    }
                },
                {
                    "Put": {
                        "TableName": table.name,
                        "Item": {
                            "PK": f"CONTA#{id_conta}",
                            "SK": f"TRANS#{timestamp}",
                            "valor": valor_reversao,
                            "tipo": tipo_reversao.value,
                            "descricao": f"Reversão de: {transacao_original['descricao']}",
                            "GSI1PK": f"CONTA#{id_conta}",
                            "GSI1SK": f"TIPO#{tipo_reversao.value}",
                            "revertida": False,
                        },
                    }
                },
                {
                    "Update": {
                        "TableName": table.name,
                        "Key": {"PK": f"CONTA#{id_conta}", "SK": sk_transacao},
                        "UpdateExpression": "SET revertida = :true",
                        "ExpressionAttributeValues": {":true": True},
                    }
                },
            ]
        )
        logger.info(f"Transação revertida com sucesso: {id_conta}, {sk_transacao}")
        return True, "Transação revertida com sucesso"
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            logger.warning(
                f"Conflito de concorrência ao reverter transação: {id_conta}, {sk_transacao}"
            )
            return False, "Conflito de concorrência: tente novamente."
        logger.error(f"Erro ao reverter transação: {e}")
        return False, str(e)
    except Exception as e:
        logger.error(f"Erro inesperado ao reverter transação: {e}")
        return False, str(e)


def buscar_transacoes_por_tipo(id_conta, tipo, limit=10):
    """
    Busca transações por tipo usando o GSI.
    """
    try:
        if not isinstance(tipo, TipoTransacao):
            raise ValueError("O tipo da transação deve ser um TipoTransacao.")

        response = table.query(
            IndexName="GSI_TipoTransacao",  # Use o nome correto do GSI
            KeyConditionExpression=Key("GSI1PK").eq(f"CONTA#{id_conta}")
            & Key("GSI1SK").begins_with(f"TIPO#{tipo.value}"),
            ScanIndexForward=False,
            Limit=limit,
        )
        logger.info(
            f"Transações por tipo consultadas com sucesso: {id_conta}, {tipo.value}"
        )
        return response.get("Items", [])
    except ClientError as e:
        logger.error(f"Erro ao buscar transações por tipo: {e}")
        raise
    except Exception as e:
        logger.error(f"Erro inesperado ao buscar transações por tipo: {e}")
        raise


def imprimir_saldo(saldo):
    """Imprime o saldo atual de forma formatada."""
    print(f"\n{'='*20}\nSaldo atual: R${saldo:.2f}\n{'='*20}")


def imprimir_historico(transacoes):
    """Imprime o histórico de transações de forma organizada."""
    print("\nHistórico de Transações:")
    print("-" * 30)
    for transacao in transacoes:
        print(
            f"{transacao['tipo'].capitalize()} | Valor: R${transacao['valor']:.2f} | Descrição: {transacao['descricao']} | Data: {transacao['SK'].replace('TRANS#', '')}"
        )
    print("-" * 30)


def imprimir_resultado_reversao(mensagem):
    """Imprime o resultado da reversão da transação."""
    print("\nResultado da Reversão:")
    print(f"{mensagem}\n{'='*20}")


def imprimir_transacoes_paginadas(transacoes, last_key):
    """Imprime as transações paginadas de forma organizada."""
    print("\nTransações Paginadas:")
    print("-" * 30)
    for transacao in transacoes:
        print(
            f"{transacao['tipo'].capitalize()} | Valor: R${transacao['valor']:.2f} | Descrição: {transacao['descricao']} | Data: {transacao['SK'].replace('TRANS#', '')}"
        )
    print("-" * 30)
    if last_key:
        print(f"Última chave avaliada: {last_key}\n{'='*20}")


# Exemplo de uso
if __name__ == "__main__":
    try:
        # Criar uma conta
        print("Criando uma nova conta...")
        id_conta = criar_conta("João Silva", 1000.00)
        print(f"Conta criada com sucesso. ID da conta: {id_conta}")

        # Consultar saldo inicial
        saldo = consultar_saldo(id_conta)
        imprimir_saldo(saldo)

        # Realizar algumas transações
        print("\nRealizando transações...")
        inserir_transacao(
            id_conta, 500.00, TipoTransacao.CREDITO, "Depósito de salário"
        )
        inserir_transacao(
            id_conta, 100.50, TipoTransacao.DEBITO, "Compra no supermercado"
        )
        inserir_transacao(
            id_conta, 200.00, TipoTransacao.DEBITO, "Pagamento de conta de luz"
        )
        inserir_transacao(
            id_conta, 50.00, TipoTransacao.CREDITO, "Reembolso de despesa"
        )

        # Consultar novo saldo
        saldo = consultar_saldo(id_conta)
        imprimir_saldo(saldo)

        # Buscar histórico de transações
        print("\nBuscando histórico de transações...")
        transacoes = buscar_historico_transacoes(id_conta)
        imprimir_historico(transacoes)

        # Verificar saldo disponível
        valor_verificacao = 300.00
        saldo_disponivel = verificar_saldo_disponivel(id_conta, valor_verificacao)
        print(
            f"\nSaldo disponível para transação de R${valor_verificacao:.2f}: {'Sim' if saldo_disponivel else 'Não'}"
        )

        # Reverter uma transação
        if transacoes:
            print("\nRevertendo a última transação...")
            ultima_transacao = transacoes[0]
            status, mensagem = reverter_transacao(id_conta, ultima_transacao["SK"])
            imprimir_resultado_reversao(mensagem)

            # Consultar saldo após reversão
            saldo = consultar_saldo(id_conta)
            imprimir_saldo(saldo)

        # Buscar transações por tipo
        print("\nBuscando transações de débito...")
        transacoes_debito = buscar_transacoes_por_tipo(id_conta, TipoTransacao.DEBITO)
        imprimir_historico(transacoes_debito)

        # Demonstrar busca paginada
        print("\nDemonstrando busca paginada...")
        pagina = 1
        last_key = None
        while True:
            transacoes, last_key = buscar_historico_paginado(
                id_conta, limit=2, last_evaluated_key=last_key
            )
            print(f"\nPágina {pagina}:")
            imprimir_transacoes_paginadas(transacoes, last_key)
            if not last_key:
                break
            pagina += 1
            # Em um cenário real, você perguntaria ao usuário se deseja carregar mais ou pararia após um certo número de páginas

    except Exception as e:
        print(f"Ocorreu um erro: {str(e)}")
