# ----------------------------------------------------------------------
# Outputs : valeurs utiles affichées après un apply.
# ----------------------------------------------------------------------

output "sns_topic_arn" {
  description = "ARN du topic SNS d'alertes (pour publier des messages de test)"
  value       = aws_sns_topic.alerts.arn
}

output "dynamodb_readings_table" {
  description = "Nom de la table DynamoDB des relevés"
  value       = aws_dynamodb_table.readings.name
}

output "dynamodb_window_state_table" {
  description = "Nom de la table DynamoDB de l'état des fenêtres glissantes"
  value       = aws_dynamodb_table.window_state.name
}

output "processor_function_name" {
  description = "Nom de la Lambda Processor (pour l'invoquer / lire ses logs)"
  value       = aws_lambda_function.processor.function_name
}

output "raw_queue_url" {
  description = "URL de la file SQS des relevés bruts (pour envoyer des messages de test)"
  value       = aws_sqs_queue.raw.url
}

output "producer_function_name" {
  description = "Nom de la Lambda Producer (pour l'invoquer manuellement)"
  value       = aws_lambda_function.producer.function_name
}
