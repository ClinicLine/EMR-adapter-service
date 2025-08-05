output "alb_dns" {
  value = module.alb.lb_dns_name
}

output "ecr_repo_url" {
  value = aws_ecr_repository.app.repository_url
}
