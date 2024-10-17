# Estrutura da Tabela DynamoDB para Gerenciador de Contas Bancárias

## Visão Geral da Tabela

Nome da Tabela: ContasCorrente

Esta tabela única armazena todos os dados relacionados às contas bancárias e suas transações, utilizando um design de tabela única do DynamoDB para máxima flexibilidade e desempenho.

## Chave Primária

A chave primária é composta por:

- **Partition Key (PK)**: AttributeName=PK, AttributeType=S (String)
- **Sort Key (SK)**: AttributeName=SK, AttributeType=S (String)

Esta estrutura permite uma organização hierárquica dos dados e consultas eficientes.

## Atributos Principais

- **PK**: Identificador da conta (ex: "CONTA#123456")
- **SK**: Identificador da transação ou metadados (ex: "TRANS#2023-10-17T14:30:00Z" ou "METADATA")
- **Saldo**: Saldo atual da conta (para itens de metadados da conta)
- **Valor**: Valor da transação
- **Tipo**: Tipo da transação (CREDITO ou DEBITO)
- **Descricao**: Descrição da transação
- **DataHora**: Timestamp da transação
- **VersaoConta**: Número de versão para controle de concorrência

## Índice Secundário Global (GSI)

Nome do GSI: GSI_TipoTransacao

Chaves do GSI:
- **Partition Key (GSI1PK)**: AttributeName=GSI1PK, AttributeType=S (String)
- **Sort Key (GSI1SK)**: AttributeName=GSI1SK, AttributeType=S (String)

Este GSI permite consultas eficientes por tipo de transação.

## Padrões de Acesso aos Dados

1. **Detalhes da Conta**:
   - PK: "CONTA#[ID_DA_CONTA]"
   - SK: "METADATA"

2. **Transações**:
   - PK: "CONTA#[ID_DA_CONTA]"
   - SK: "TRANS#[TIMESTAMP]"

3. **Consulta por Tipo de Transação** (usando GSI):
   - GSI1PK: "CONTA#[ID_DA_CONTA]#[TIPO]" (ex: "CONTA#123456#CREDITO")
   - GSI1SK: [TIMESTAMP]

## Exemplo de Item (Transação)

```json
{
  "PK": "CONTA#123456",
  "SK": "TRANS#2023-10-17T14:30:00Z",
  "GSI1PK": "CONTA#123456#CREDITO",
  "GSI1SK": "2023-10-17T14:30:00Z",
  "Valor": 100.00,
  "Tipo": "CREDITO",
  "Descricao": "Depósito em dinheiro",
  "DataHora": "2023-10-17T14:30:00Z"
}
```

## Exemplo de Item (Metadados da Conta)

```json
{
  "PK": "CONTA#123456",
  "SK": "METADATA",
  "Saldo": 1500.00,
  "VersaoConta": 5,
  "NomeTitular": "João Silva",
  "DataAbertura": "2023-01-01"
}
```

Esta estrutura permite operações eficientes como:
- Recuperar detalhes da conta
- Listar transações de uma conta
- Consultar transações por tipo
- Realizar atualizações atômicas no saldo da conta e registrar transações simultaneamente

