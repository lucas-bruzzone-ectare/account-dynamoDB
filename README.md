# Conta Corrente com DynamoDB

Este projeto é uma implementação de um sistema de contas correntes usando o Amazon DynamoDB como banco de dados. Ele permite criar contas, realizar transações (créditos e débitos), transferências entre contas, e consultar o histórico de transações.

## Funcionalidades

- Criar contas com saldo inicial.
- Inserir transações (créditos e débitos).
- Realizar transferências entre contas.
- Consultar saldo atual de uma conta.
- Buscar histórico de transações, incluindo paginação.
- Reverter transações específicas.
- Verificar saldo disponível para uma transação.
- Gerar relatórios simples de transações em um período específico.

## Pré-requisitos

Antes de começar, você precisará ter:

- Python 3.x instalado.
- A biblioteca `boto3` instalada. Você pode instalá-la usando o seguinte comando:

```bash
pip install boto3
```

- Acesso ao AWS e configurações adequadas para o DynamoDB.

## Estrutura do Código

O código principal está dividido em várias funções que executam tarefas específicas relacionadas à gestão de contas correntes:

### Funções Principais

- **`criar_conta(nome_titular, saldo_inicial)`**
  - Cria uma nova conta com um saldo inicial especificado.
  
- **`inserir_transacao(id_conta, valor, tipo, descricao)`**
  - Insere uma nova transação (crédito ou débito) e atualiza o saldo da conta correspondente.

- **`consultar_saldo(id_conta)`**
  - Retorna o saldo atual de uma conta.

- **`buscar_historico_transacoes(id_conta, limit=10)`**
  - Busca o histórico de transações para uma conta, limitando o número de resultados.

- **`verificar_saldo_disponivel(id_conta, valor)`**
  - Verifica se há saldo suficiente na conta para realizar uma transação.

- **`transferir_entre_contas(id_conta_origem, id_conta_destino, valor, descricao)`**
  - Realiza uma transferência entre duas contas, debitando uma e creditando a outra.

- **`reverter_transacao(id_conta, sk_transacao)`**
  - Reverte uma transação específica, ajustando o saldo da conta.

- **`gerar_relatorio_simples(id_conta, periodo_dias=30)`**
  - Gera um relatório simples com agregações básicas sobre transações em um período específico.

## Demonstração

No bloco `if __name__ == "__main__":`, uma demonstração completa das funcionalidades é executada. As etapas incluem:

1. Criar contas para dois usuários (Alice e Bob).
2. Consultar os saldos iniciais das contas.
3. Realizar transações de crédito e débito.
4. Transferir dinheiro entre as contas de Alice e Bob.
5. Consultar saldos após as transações.
6. Buscar histórico de transações com paginação.
7. Reverter uma transação específica.
8. Verificar se há saldo disponível para uma transação.
9. Gerar um relatório simples sobre transações nos últimos 7 dias.
10. Consultar saldos finais das contas.

## Conclusão

Este projeto fornece uma base sólida para a gestão de contas correntes utilizando o DynamoDB. Você pode expandir suas funcionalidades, como adicionar autenticação, melhorar a interface de usuário ou integrar com outras APIs.

## Licença

Este projeto está sob a Licença MIT - consulte o arquivo [LICENSE](LICENSE) para mais detalhes.