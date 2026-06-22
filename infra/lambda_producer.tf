# ----------------------------------------------------------------------
# Lambda Producer : génère des relevés et les envoie dans la file SQS.
# ----------------------------------------------------------------------

data "archive_file" "producer" {
  type        = "zip"
  source_dir  = "${path.module}/lambdas/producer"
  output_path = "${path.module}/builds/producer.zip"
}

# Rôle d'exécution (réutilise le même "assume role" que le processor).
resource "aws_iam_role" "producer" {
  name               = "${var.project_name}-producer-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy_attachment" "producer_logs" {
  role       = aws_iam_role.producer.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Seule permission métier : envoyer des messages dans la file "raw".
data "aws_iam_policy_document" "producer_perms" {
  statement {
    sid       = "SqsSend"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.raw.arn]
  }
}

resource "aws_iam_role_policy" "producer_perms" {
  name   = "${var.project_name}-producer-perms"
  role   = aws_iam_role.producer.id
  policy = data.aws_iam_policy_document.producer_perms.json
}

resource "aws_lambda_function" "producer" {
  function_name = "${var.project_name}-producer"
  role          = aws_iam_role.producer.arn
  runtime       = "python3.12"
  handler       = "handler.handler"
  timeout       = 30

  filename         = data.archive_file.producer.output_path
  source_code_hash = data.archive_file.producer.output_base64sha256

  environment {
    variables = {
      RAW_QUEUE_URL = aws_sqs_queue.raw.url
      N_STATIONS    = "5"
    }
  }
}
