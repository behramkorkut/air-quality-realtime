# ----------------------------------------------------------------------
# SQS : la file des relevés bruts. Remplace le topic Redpanda
# "air-quality-raw". Le Producer y dépose, le Processor y est déclenché.
# Free tier : 1 million de requêtes/mois gratuites.
# ----------------------------------------------------------------------

# Dead-letter queue : recueille les messages qui échouent au traitement
# (après 3 tentatives) au lieu de les rejouer indéfiniment.
resource "aws_sqs_queue" "raw_dlq" {
  name = "${var.project_name}-raw-dlq"
}

# File principale.
resource "aws_sqs_queue" "raw" {
  name                       = "${var.project_name}-raw"
  visibility_timeout_seconds = 60 # >= timeout de la Lambda (30 s), recommandé x2+

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.raw_dlq.arn
    maxReceiveCount     = 3
  })
}

# ----------------------------------------------------------------------
# Event source mapping : c'est ce qui fait que CHAQUE message arrivant
# dans la file déclenche automatiquement la Lambda Processor.
# (équivalent du "consumer group" Kafka du projet d'origine)
# ----------------------------------------------------------------------
resource "aws_lambda_event_source_mapping" "raw_to_processor" {
  event_source_arn = aws_sqs_queue.raw.arn
  function_name    = aws_lambda_function.processor.arn
  batch_size       = 10
}
