# Stores the last-processed PDF filename per school level.
# Lambda checks these before parsing to skip months it has already processed.

resource "aws_ssm_parameter" "last_pdf" {
  for_each = toset(["elementary", "middle", "high"])

  name  = "/${var.project}/last-pdf/${each.key}"
  type  = "String"
  value = "none"

  lifecycle {
    # Lambda updates these values; Terraform should not overwrite them after creation
    ignore_changes = [value]
  }
}
