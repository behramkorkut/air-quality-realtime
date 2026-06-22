# ----------------------------------------------------------------------
# Variables d'entrée du projet d'infrastructure.
# ----------------------------------------------------------------------

variable "aws_region" {
  description = "Région AWS où déployer les ressources"
  type        = string
  default     = "eu-west-3" # Paris
}

variable "project_name" {
  description = "Préfixe commun à toutes les ressources (noms + tags)"
  type        = string
  default     = "air-quality-realtime"
}

variable "alert_email" {
  description = "Adresse email qui recevra les alertes de dépassement (abonnement SNS)"
  type        = string
  # Pas de valeur par défaut : on la fournit via terraform.tfvars (non commité).
}

variable "producer_schedule" {
  description = "Fréquence de déclenchement du Producer par EventBridge (expression rate/cron)"
  type        = string
  default     = "rate(5 minutes)"
}
