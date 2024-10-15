# Gerenciador de Contas Corrente

Este projeto é um sistema simples de gerenciamento de contas correntes usando o AWS DynamoDB. Permite criar contas, realizar transações (créditos e débitos), consultar saldos, reverter transações e buscar o histórico de transações.

## Funcionalidades

- **Criar Conta:** Cria uma nova conta com um saldo inicial.
- **Inserir Transação:** Insere transações de crédito ou débito e atualiza o saldo da conta.
- **Consultar Saldo:** Consulta o saldo atual da conta.
- **Buscar Histórico de Transações:** Busca e exibe o histórico de transações realizadas.
- **Reverter Transação:** Reverte uma transação específica, ajustando o saldo da conta.
- **Verificar Saldo Disponível:** Verifica se há saldo disponível para uma transação específica.
- **Buscar Histórico Paginado:** Permite a busca do histórico de transações com paginação.

## Pré-requisitos

Para executar este código, você precisará de:

- Python 3.x
- Boto3 (biblioteca AWS SDK para Python)
- Conta da AWS com acesso ao DynamoDB
- Configurar credenciais AWS (usando o arquivo `~/.aws/credentials` ou variáveis de ambiente)

## Instalação

1. Clone este repositório:

   ```bash
   git clone <URL_DO_REPOSITORIO>
   cd <NOME_DO_DIRETORIO>
   ```

2. Instale as dependências necessárias:

   ```bash
   pip install boto3
   ```

3. Crie uma tabela no DynamoDB chamada `ContasCorrente` com a seguinte estrutura:

   - **Partition Key:** `PK` (String)
   - **Sort Key:** `SK` (String)

## Uso

Para executar o código, basta rodar o script principal:

```bash
python poc.py
```

O exemplo de uso no final do script principal demonstra como criar uma conta, realizar transações, consultar saldo, reverter uma transação, verificar saldo disponível e buscar histórico paginado.

### Exemplo de Uso

O código no final do script principal oferece um exemplo de uso das funcionalidades. Aqui está uma breve descrição do que ele faz:

1. Cria uma nova conta para um titular chamado "João Silva" com um saldo inicial de R$1000,00.
2. Insere uma transação de crédito de R$200,00 e uma transação de débito de R$50,00.
3. Consulta e imprime o saldo atual da conta.
4. Busca e imprime o histórico de transações realizadas.
5. Reverte a última transação do histórico.
6. Verifica se há saldo disponível para uma transação de R$50,00.
7. Busca e imprime o histórico de transações com paginação.

## Funções Principais

### `criar_conta(nome_titular, saldo_inicial)`

Cria uma nova conta com um saldo inicial.

- **Parâmetros:**
  - `nome_titular` (str): Nome do titular da conta.
  - `saldo_inicial` (float): Saldo inicial da conta.
- **Retorna:** ID da conta criada.

### `inserir_transacao(id_conta, valor, tipo, descricao)`

Insere uma nova transação e atualiza o saldo da conta.

- **Parâmetros:**
  - `id_conta` (str): ID da conta.
  - `valor` (float): Valor da transação.
  - `tipo` (str): Tipo da transação ('credito' ou 'debito').
  - `descricao` (str): Descrição da transação.
- **Retorna:** Novo saldo após a transação.

### `consultar_saldo(id_conta)`

Consulta o saldo atual da conta.

- **Parâmetros:**
  - `id_conta` (str): ID da conta.
- **Retorna:** Saldo atual da conta.

### `buscar_historico_transacoes(id_conta, limit=10)`

Busca o histórico de transações por conta.

- **Parâmetros:**
  - `id_conta` (str): ID da conta.
  - `limit` (int): Limite de transações a serem retornadas.
- **Retorna:** Lista de transações.