# ----------------------------------------------------------------------
# EventBridge : déclenche le Producer périodiquement.
# Remplace l'orchestration horaire (Airflow) du projet d'origine.
# Une règle "schedule" est gratuite.
# ----------------------------------------------------------------------

resource "aws_cloudwatch_event_rule" "producer_schedule" {
  name                = "${var.project_name}-producer-schedule"
  description         = "Déclenche le Producer pour générer des relevés"
  schedule_expression = var.producer_schedule
}

# Cible de la règle : la Lambda Producer.
resource "aws_cloudwatch_event_target" "producer" {
  rule = aws_cloudwatch_event_rule.producer_schedule.name
  arn  = aws_lambda_function.producer.arn
}

# Autorise EventBridge à invoquer la Lambda (permission basée sur les ressources).
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.producer.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.producer_schedule.arn
}
