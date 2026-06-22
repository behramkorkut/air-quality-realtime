# ----------------------------------------------------------------------
# DynamoDB : remplace l'entrepôt DuckDB local du projet.
#
# Mode PAY_PER_REQUEST (on-demand) : pas de capacité à provisionner, on
# paie à la requête. Pour une démo (quelques centaines d'écritures), le
# coût est de l'ordre de zéro, et le free tier couvre 25 Go de stockage.
#
# DynamoDB est "schemaless" : on ne déclare QUE les attributs qui servent
# de clés. Les autres champs (pm25, no2, ...) sont écrits librement.
# ----------------------------------------------------------------------

# Table 1 : l'historique des relevés.
# Clé de partition = station, clé de tri = horodatage -> on peut requêter
# "tous les relevés d'une station, triés dans le temps".
resource "aws_dynamodb_table" "readings" {
  name         = "${var.project_name}-readings"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "station_id"
  range_key    = "timestamp"

  attribute {
    name = "station_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }
}

# Table 2 : l'état de la fenêtre glissante par (station, polluant).
# Indispensable car une Lambda est SANS état entre deux appels : on
# externalise ici la mémoire que ton AlertDetector gardait en RAM
# (les dernières valeurs + le flag "en alerte" pour l'edge-trigger).
# Clé = "station_id#pollutant".
resource "aws_dynamodb_table" "window_state" {
  name         = "${var.project_name}-window-state"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"

  attribute {
    name = "pk"
    type = "S"
  }
}
