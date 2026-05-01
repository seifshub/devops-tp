terraform {
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
  }
}

# Connect Terraform to your local Minikube cluster
provider "kubernetes" {
  config_path    = "~/.kube/config"
  config_context = "minikube"
}

# Create a dedicated namespace for our app
resource "kubernetes_namespace" "app" {
  metadata {
    name = "flask-app"
    labels = {
      environment = "production"
      managed-by  = "terraform"
    }
  }
}

# Create a namespace for monitoring tools
resource "kubernetes_namespace" "monitoring" {
  metadata {
    name = "monitoring"
    labels = {
      managed-by = "terraform"
    }
  }
}

# Output the namespace names so Ansible can use them
output "app_namespace" {
  value = kubernetes_namespace.app.metadata[0].name
}

output "monitoring_namespace" {
  value = kubernetes_namespace.monitoring.metadata[0].name
}
