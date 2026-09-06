resource "kubernetes_namespace" "argocd" {
  metadata {
    name = var.namespace
  }
}

resource "helm_release" "argocd" {
  name       = "argocd"
  namespace  = kubernetes_namespace.argocd.metadata[0].name
  repository = "https://argoproj.github.io/argo-helm"
  chart      = "argo-cd"
  version    = var.argocd_chart_version

  values = [
    templatefile("${path.module}/values/argocd-values.yaml", {
      gitops_repo_url        = var.gitops_repo_url
      gitops_target_revision = var.gitops_target_revision
      argocd_namespace       = var.namespace
    })
  ]

  timeout          = 600
  wait             = true
  create_namespace = false

  depends_on = [kubernetes_namespace.argocd]
}
