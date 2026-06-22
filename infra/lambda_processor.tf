# ----------------------------------------------------------------------
# Lambda Processor : consomme les relevés, détecte les dépassements,
# stocke dans DynamoDB et publie les alertes sur SNS.
# ----------------------------------------------------------------------

# --- 1. Empaquetage du code en zip ---
# archive_file zippe le dossier du handler. Pas de dépendance externe
# (stdlib + boto3 fourni par AWS) -> le zip ne contient que handler.py.
data "archive_file" "processor" {
  type        = "zip"
  source_dir  = "${path.module}/lambdas/processor"
  output_path = "${path.module}/builds/processor.zip"
}

# --- 2. Rôle d'exécution de la Lambda ---
# "assume role" : autorise le service Lambda à endosser ce rôle.
data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "processor" {
  name               = "${var.project_name}-processor-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

# Logs CloudWatch (politique gérée par AWS, le strict nécessaire).
resource "aws_iam_role_policy_attachment" "processor_logs" {
  role       = aws_iam_role.processor.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Permissions métier au plus juste (least privilege) :
# écrire/lire les 2 tables DynamoDB + publier sur le topic SNS.
data "aws_iam_policy_document" "processor_perms" {
  statement {
    sid     = "DynamoReadWrite"
    actions = ["dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:UpdateItem"]
    resources = [
      aws_dynamodb_table.readings.arn,
      aws_dynamodb_table.window_state.arn,
    ]
  }

  statement {
    sid       = "SnsPublish"
    actions   = ["sns:Publish"]
    resources = [aws_sns_topic.alerts.arn]
  }

  # Consommer la file SQS (requis par l'event source mapping).
  statement {
    sid = "SqsConsume"
    actions = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
    ]
    resources = [aws_sqs_queue.raw.arn]
  }
}

resource "aws_iam_role_policy" "processor_perms" {
  name   = "${var.project_name}-processor-perms"
  role   = aws_iam_role.processor.id
  policy = data.aws_iam_policy_document.processor_perms.json
}

# --- 3. La fonction Lambda ---
resource "aws_lambda_function" "processor" {
  function_name = "${var.project_name}-processor"
  role          = aws_iam_role.processor.arn
  runtime       = "python3.12"
  handler       = "handler.handler"
  timeout       = 30

  filename         = data.archive_file.processor.output_path
  # source_code_hash : si le code change, Terraform redéploie la Lambda.
  source_code_hash = data.archive_file.processor.output_base64sha256

  environment {
    variables = {
      SNS_TOPIC_ARN      = aws_sns_topic.alerts.arn
      READINGS_TABLE     = aws_dynamodb_table.readings.name
      WINDOW_STATE_TABLE = aws_dynamodb_table.window_state.name
      WINDOW_SIZE        = "5"
    }
  }
}
