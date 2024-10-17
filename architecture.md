
# API de Conta Corrente

## 1. Gerenciamento de Contas

- **Método**: `POST`
- **Rota**: `/account`
- **Lambda**: `createAccount`
  - **Body**:
    ```json
    {
      "name": "João Silva",
      "email": "joao.silva@email.com",
      "initialBalance": 1000
    }
    ```

- **Método**: `GET`
- **Rota**: `/account/{accountId}/balance`
- **Lambda**: `getBalance`

## 2. Processamento de Transações

- **Método**: `POST`
- **Rota**: `/account/{accountId}/deposit`
- **Lambda**: `deposit`
  - **Body**:
    ```json
    {
      "amount": 500
    }
    ```



- **Método**: `POST`
- **Rota**: `/account/{accountId}/withdraw`
- **Lambda**: `withdraw`
  - **Body**:
    ```json
    {
      "amount": 300
    }
    ```

- **Método**: `GET`
- **Rota**: `/account/{accountId}/transactions`
- **Lambda**: `getTransactionHistory`

- **Método**: `POST`
- **Rota**: `/account/{accountId}/transactions/{transactionId}/revert`
- **Lambda**: `revertTransaction`
  - **Body**:
    ```json
    {
      "reason": "Duplicated transaction"
    }
    ```

## 3. Consultas Avançadas

- **Método**: `GET`
- **Rota**: `/account/{accountId}/transactions/paginated?pageToken={token}&limit={limit}`
- **Lambda**: `getPaginatedTransactionHistory`

- **Método**: `GET`
- **Rota**: `/account/{accountId}/transactions/type/{type}`
- **Lambda**: `filterTransactionsByType`
