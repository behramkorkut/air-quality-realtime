# ----------------------------------------------------------------------
# SNS : le canal d'alertes.
# - un "topic" = un canal de publication/abonnement
# - une "subscription" email = ton adresse reçoit chaque message publié
#
# Remplace le topic Redpanda "air-quality-alerts" du projet local.
# Free tier : 1000 notifications email/mois gratuites.
# ----------------------------------------------------------------------

resource "aws_sns_topic" "alerts" {
  name = "${var.project_name}-alerts"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
  # Après l'apply, AWS envoie un mail de confirmation à cette adresse.
  # Il faut cliquer le lien pour activer l'abonnement (sinon : "PendingConfirmation").
}
