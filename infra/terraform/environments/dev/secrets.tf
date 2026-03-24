resource "aws_secretsmanager_secret" "runtime" {
  for_each = local.secret_names

  name                    = each.value
  description             = "Deploy-time secret container for ${each.key}."
  recovery_window_in_days = 7

  tags = {
    Name               = each.value
    Component          = "secrets"
    Role               = each.key
    DataClassification = "private"
  }
}
