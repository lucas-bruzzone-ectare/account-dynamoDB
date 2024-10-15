Explicação detalhada da estrutura:

Tabela Principal (ContasCorrente):
A tabela principal usa uma estrutura de chave composta:

Chave de Partição (PK): CONTA#<id_conta>
Chave de Ordenação (SK): Varia entre "METADATA" e "TRANS#<timestamp>"

Esta estrutura permite armazenar eficientemente tanto os metadados da conta quanto as transações associadas a ela.
a) Metadados da Conta:

PK: CONTA#<id_conta>
SK: METADATA
Atributos: nome_titular, saldo_atual, status

Exemplo:
{
PK: "CONTA#123",
SK: "METADATA",
nome_titular: "João Silva",
saldo_atual: 1000.00,
status: "ativo"
}
b) Transações:

PK: CONTA#<id_conta>
SK: TRANS#<timestamp>
Atributos: valor, tipo (crédito/débito), descricao

Exemplo:
{
PK: "CONTA#123",
SK: "TRANS#2024-10-15T14:30:00",
valor: 500.00,
tipo: "crédito",
descricao: "Depósito"
}
Índice Secundário Global (GSI_TipoTransacao):
Este GSI permite consultas eficientes por tipo de transação:

PK: CONTA#<id_conta>
SK: TIPO#<tipo_transacao>

Exemplo de item no GSI:
{
PK: "CONTA#123",
SK: "TIPO#credito",
valor: 500.00,
timestamp: "2024-10-15T14:30:00",
descricao: "Depósito"
}

Implementação dos padrões de acesso:

Inserir nova transação:

Crie um novo item na tabela principal com PK=CONTA#<id_conta> e SK=TRANS#<timestamp>
Atualize o item de metadados (SK=METADATA) para refletir o novo saldo
Adicione um item correspondente no GSI_TipoTransacao


Consultar saldo atual:

Faça uma operação GetItem com PK=CONTA#<id_conta> e SK=METADATA


Buscar histórico de transações:

Execute uma Query na tabela principal usando PK=CONTA#<id_conta> e SK começando com "TRANS#"
Use ScanIndexForward para controlar a ordem (crescente ou decrescente)


Atualizar saldo após transação:

Utilize uma operação UpdateItem no item de metadados (SK=METADATA)
Use expressões de atualização condicional para garantir consistência


Verificar saldo disponível:

Mesma operação da consulta de saldo atual (GetItem)



Vantagens desta modelagem:

Escalabilidade: O uso do ID da conta como chave de partição distribui eficientemente os dados entre as partições do DynamoDB.
Velocidade: Acesso rápido aos dados da conta e transações usando a combinação de PK e SK. Consultas eficientes por tipo de transação usando o GSI.
Simplicidade: Estrutura clara e direta, facilitando operações CRUD e manutenção.
Flexibilidade: O modelo suporta facilmente a adição de novos tipos de transações ou atributos adicionais sem alterações estruturais.
Consistência: Manter os metadados da conta (incluindo saldo) no mesmo item que as transações permite atualizações atômicas e consistentes.

Esta estrutura otimizada para o DynamoDB permite operações eficientes e escaláveis para uma POC de conta corrente, atendendo aos padrões de acesso especificados e aproveitando as características únicas do banco de dados NoSQL. Cop
