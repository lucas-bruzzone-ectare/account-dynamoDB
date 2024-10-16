# Gerenciador de Contas Bancárias com DynamoDB

## Visão Geral

O Gerenciador de Contas Bancárias com DynamoDB é uma solução robusta e eficiente para gerenciar contas bancárias usando o Amazon DynamoDB. Este sistema fornece um conjunto abrangente de recursos para gerenciamento de contas, processamento de transações e manutenção de registros financeiros, tudo isso aproveitando o poder e a escalabilidade do DynamoDB.

## Principais Recursos

### 1. Gerenciamento de Contas
- **Criar Contas**: Configure facilmente novas contas bancárias com saldos iniciais.
- **Consultas de Saldo**: Verifique rapidamente os saldos das contas em tempo real.

### 2. Processamento de Transações
- **Depósitos e Saques**: Processe créditos e débitos com atualizações automáticas de saldo.
- **Histórico de Transações**: Mantenha um registro detalhado de todas as atividades da conta.
- **Reversão de Transações**: Capacidade de reverter transações, garantindo a integridade dos dados.

### 3. Consultas Avançadas
- **Histórico de Transações Paginado**: Recupere eficientemente o histórico de transações em partes gerenciáveis.
- **Pesquisa de Transações por Tipo**: Encontre rapidamente todas as transações de crédito ou débito de uma conta.

### 4. Consistência e Integridade de Dados
- **Transações Atômicas**: Garanta que operações relacionadas (como atualizar o saldo e registrar uma transação) sejam realizadas como uma única unidade indivisível.
- **Bloqueio Otimista**: Previna conflitos de dados em operações concorrentes usando números de versão.

## Destaques Técnicos

Embora o sistema seja projetado para facilidade de uso, ele é construído sobre uma base de recursos técnicos robustos:

### Modelo de Dados do DynamoDB
- **Chave Primária**: Chave composta (PK: ID da Conta, SK: ID da Transação/METADATA) para acesso eficiente aos dados.
- **Índice Secundário Global (GSI)**: Permite a rápida recuperação de transações por tipo (crédito/débito).

### Transações Atômicas
Todas as operações críticas (como processar uma transação) usam o recurso de escrita transacional do DynamoDB, garantindo que várias alterações relacionadas sejam aplicadas como uma única unidade atômica. Isso evita inconsistências como saldos e registros de transações incompatíveis.

### Controle de Concorrência
O sistema usa um número de versão para cada conta para detectar e prevenir conflitos em operações concorrentes, garantindo a integridade dos dados sem sacrificar o desempenho.
---