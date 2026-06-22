# ----------------------------------------------------------------------
# Versions de Terraform et des providers requis.
# On épingle les versions pour des déploiements reproductibles.
# ----------------------------------------------------------------------
terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    # archive : sert à zipper le code des Lambdas (étapes suivantes).
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }
}
