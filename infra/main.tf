terraform {
  required_version = ">= 1.4.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

############################
# 1. VPC (public only for demo)
############################
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.0.0"

  name = "clinicline-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["${var.aws_region}a", "${var.aws_region}b"]
  public_subnets  = ["10.0.1.0/24", "10.0.2.0/24"]
  enable_nat_gateway = false
}

############################
# 2. ECR repository for Docker images
############################
resource "aws_ecr_repository" "app" {
  name = "accuro-adapter"
}

############################
# 3. Secrets Manager secrets (placeholders)
############################
resource "aws_secretsmanager_secret" "accuro" {
  name = "/clinicline/accuro"
}

resource "aws_secretsmanager_secret" "retell" {
  name = "/clinicline/retell/webhook"
}

############################
# 4. ECS Cluster & Fargate Service
############################
module "ecs" {
  source  = "terraform-aws-modules/ecs/aws"
  version = "5.1.1"

  cluster_name = "clinicline-cluster"

  # Task definition
  task_exec_iam_role_name = "ecsTaskExecutionRole"

  task_images = [
    {
      name         = "app"
      repository   = aws_ecr_repository.app.repository_url
      tag          = var.image_tag
      cpu          = 256
      memory       = 512
      port_mappings = [{ containerPort = var.container_port }]
      environment  = [
        { name = "PORT", value = tostring(var.container_port) }
      ]
      secrets      = [
        { name = "ACCURO_SECRET",       value_from = aws_secretsmanager_secret.accuro.arn },
        { name = "RETELL_WEBHOOK_KEY", value_from = aws_secretsmanager_secret.retell.arn }
      ]
    }
  ]

  subnet_ids         = module.vpc.public_subnets
  security_group_ids = []
  assign_public_ip   = true
}

############################
# 5. Application Load Balancer
############################
module "alb" {
  source  = "terraform-aws-modules/alb/aws"
  version = "9.5.0"

  name               = "clinicline-alb"
  load_balancer_type = "application"
  vpc_id             = module.vpc.vpc_id
  subnets            = module.vpc.public_subnets

  target_groups = [
    {
      name_prefix  = "api"
      port         = var.container_port
      protocol     = "HTTP"
      target_type  = "ip"
      health_check = { path = "/healthz" }
    }
  ]

  listeners = [
    {
      port               = 443
      protocol           = "HTTPS"
      ssl_policy         = "ELBSecurityPolicy-TLS13-1-2-2021-06"
      certificate_arn    = aws_acm_certificate.cert.arn
      target_group_index = 0
    }
  ]
}

############################
# 6. ACM certificate & DNS
############################
resource "aws_acm_certificate" "cert" {
  domain_name       = var.domain_name
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

data "aws_route53_zone" "primary" {
  name = var.root_domain
}

resource "aws_route53_record" "cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.cert.domain_validation_options : dvo.domain_name => {
      name  = dvo.resource_record_name
      type  = dvo.resource_record_type
      value = dvo.resource_record_value
    }
  }
  zone_id = data.aws_route53_zone.primary.zone_id
  name    = each.value.name
  type    = each.value.type
  ttl     = 300
  records = [each.value.value]
}

resource "aws_acm_certificate_validation" "cert_val" {
  certificate_arn         = aws_acm_certificate.cert.arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}

resource "aws_route53_record" "api" {
  zone_id = data.aws_route53_zone.primary.zone_id
  name    = var.domain_name
  type    = "A"
  alias {
    name                   = module.alb.lb_dns_name
    zone_id                = module.alb.lb_zone_id
    evaluate_target_health = true
  }
}
