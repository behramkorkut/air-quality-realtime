# Infrastructure AWS (Terraform) — déploiement serverless

Ce dossier déploie le pipeline *Air Quality Realtime* sur **AWS en mode
serverless**, entièrement décrit en **Terraform** (Infrastructure as Code).

L'architecture locale du projet (Redpanda + Airflow + DuckDB, conteneurisée)
est ici transposée vers des services **managés et éligibles au free tier AWS**,
sans rien à administrer.

## Architecture

```
 EventBridge (toutes les 5 min)
        │  déclenche
        ▼
 ┌──────────────┐   relevés JSON     ┌──────────────┐
 │  Lambda      │ ─────────────────► │   SQS        │
 │  Producer    │                    │  file "raw"  │
 │  (simulateur)│                    │  (+ DLQ)     │
 └──────────────┘                    └──────┬───────┘
                                            │ event source mapping
                                            ▼
                                     ┌──────────────┐   si dépassement   ┌──────────┐
                                     │  Lambda      │ ─────────────────► │   SNS    │ ──► 📧 email
                                     │  Processor   │   (edge-trigger)   │ "alerts" │
                                     │  (détection) │                    └──────────┘
                                     └──────┬───────┘
                                            │ relevés + état fenêtre glissante
                                            ▼
                                     ┌──────────────┐
                                     │  DynamoDB    │  (2 tables)
                                     └──────────────┘
```

## Correspondance avec le projet local

| Brique locale              | Service AWS              | Rôle                                   |
|----------------------------|--------------------------|----------------------------------------|
| Topic Redpanda `raw`       | **SQS** (+ DLQ)          | File des relevés bruts                 |
| Processor (consumer group) | **Lambda** Processor     | Détection de dépassements (edge-trigger) |
| Producer                   | **Lambda** Producer      | Génération des relevés                 |
| Entrepôt DuckDB            | **DynamoDB** (2 tables)  | Stockage relevés + état des fenêtres   |
| Topic Redpanda `alerts`    | **SNS** (email)          | Notification des alertes               |
| Orchestration Airflow      | **EventBridge** (rule)   | Déclenchement périodique               |

La logique métier (moyenne glissante sur fenêtre + déclenchement *edge-triggered*
au passage du seuil OMS) est portée fidèlement depuis `processor/detector.py`.
Seule adaptation imposée par le serverless : l'état de la fenêtre glissante est
persisté dans DynamoDB (les Lambdas sont sans état entre deux invocations).

## Pourquoi le free tier est respecté

| Service     | Quota gratuit / mois        | Usage de la démo |
|-------------|-----------------------------|------------------|
| Lambda      | 1 M requêtes                | quelques dizaines |
| SQS         | 1 M requêtes                | quelques dizaines |
| DynamoDB    | 25 Go + on-demand           | quelques Ko       |
| SNS         | 1000 emails                 | quelques emails   |
| EventBridge | règles planifiées gratuites | 1 règle           |

Toutes les ressources portent les `default_tags` `Project = air-quality-realtime`
et `ManagedBy = terraform`, pour les retrouver et les nettoyer facilement.

## Prérequis

- [Terraform](https://developer.hashicorp.com/terraform) >= 1.5
- [AWS CLI](https://aws.amazon.com/cli/) configuré (`aws configure`)
- Un compte AWS (un utilisateur IAM dédié, pas le compte root)

## Déploiement

```bash
# 1. Renseigner l'email qui recevra les alertes
cp terraform.tfvars.example terraform.tfvars
#   puis éditer alert_email dans terraform.tfvars

# 2. Initialiser et déployer
terraform init
terraform plan
terraform apply

# 3. Confirmer l'abonnement SNS : cliquer le lien reçu par email.
```

## Tester

```bash
# Invoquer le Producer une fois (sinon EventBridge le fait toutes les 5 min)
aws lambda invoke \
  --function-name "$(terraform output -raw producer_function_name)" \
  --cli-binary-format raw-in-base64-out --payload '{}' /dev/stdout

# Compter les relevés stockés dans DynamoDB
aws dynamodb scan \
  --table-name "$(terraform output -raw dynamodb_readings_table)" --select COUNT

# Suivre les logs du Processor
aws logs tail "/aws/lambda/air-quality-realtime-processor" --follow
```

## Nettoyage

```bash
terraform destroy
```

Supprime **toutes** les ressources (et coupe les emails). Le code `.tf` reste :
tout est recréable en un `terraform apply`.

## Organisation des fichiers

| Fichier               | Contenu                                            |
|-----------------------|----------------------------------------------------|
| `versions.tf`         | Versions de Terraform et des providers             |
| `providers.tf`        | Provider AWS + tags par défaut                     |
| `variables.tf`        | Variables d'entrée                                 |
| `sns.tf`              | Topic d'alertes + abonnement email                 |
| `dynamodb.tf`         | Tables relevés + état des fenêtres                 |
| `sqs.tf`              | File `raw` + DLQ + event source mapping            |
| `lambda_processor.tf` | Lambda Processor + rôle IAM (least privilege)      |
| `lambda_producer.tf`  | Lambda Producer + rôle IAM                         |
| `eventbridge.tf`      | Planification du Producer                          |
| `outputs.tf`          | Valeurs utiles (ARN, noms de ressources)           |
| `lambdas/`            | Code Python des deux Lambdas (stdlib + boto3)      |
