output "argocd_namespace" {
  description = "Namespace where Argo CD is installed."
  value       = var.namespace
}

output "argocd_release_name" {
  description = "Helm release name."
  value       = helm_release.argocd.name
}

output "argocd_ui_port_forward" {
  description = "Command to open Argo CD UI locally."
  value       = "kubectl -n ${var.namespace} port-forward svc/argocd-server 8080:80"
}

output "argocd_initial_admin_password" {
  description = "Command to read the initial Argo CD admin password."
  value       = "kubectl -n ${var.namespace} get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d"
}

output "applications_check" {
  description = "Command to check generated Argo CD Applications."
  value       = "kubectl get applications -n ${var.namespace}"
}
