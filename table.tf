# Recurso da tabela DynamoDB
resource "aws_dynamodb_table" "contas_corrente" {
  name           = "ContasCorrente"
  billing_mode   = "PAY_PER_REQUEST"  # Modo de cobrança sob demanda
  hash_key       = "PK"
  range_key      = "SK"

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  attribute {
    name = "GSI1PK"
    type = "S"
  }

  attribute {
    name = "GSI1SK"
    type = "S"
  }

  # Índice Secundário Global (GSI) para consultas por tipo de transação
  global_secondary_index {
    name               = "GSI_TipoTransacao"
    hash_key           = "GSI1PK"
    range_key          = "GSI1SK"
    projection_type    = "ALL"
  }

  tags = {
    Environment = "POC"
    Project     = "ContaCorrente"
  }
}