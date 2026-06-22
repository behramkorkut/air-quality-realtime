# ----------------------------------------------------------------------
# Configuration du provider AWS.
# Les clés ne sont PAS ici : Terraform les lit dans ~/.aws/credentials.
#
# default_tags : ces tags sont appliqués AUTOMATIQUEMENT à toutes les
# ressources créées par ce provider. Très pratique pour identifier et
# retrouver (ou nettoyer) tout ce qui appartient au projet.
# ----------------------------------------------------------------------
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = var.project_name
      ManagedBy = "terraform"
      Repo      = "air-quality-realtime"
    }
  }
}
