# Final Project: Production-ready MLOps platform

Проєкт збирає компоненти з попередніх ДЗ у єдину MLOps-платформу в AWS: EKS, Argo CD, MLflow Model Registry, inference API, моніторинг, security baseline і контрольований deployment моделі.

## Scope

Реалізуються обов'язкові блоки A-D і рекомендовані блоки E-F. Бонусні завдання не входять у scope. Локальний fallback не використовується, основний сценарій - AWS/EKS.

## Архітектура

```text
GitHub push
  -> GitHub Actions training workflow
  -> AWS Step Functions
  -> training job registers model in MLflow Registry as Staging
  -> manual promotion script moves model to Production
  -> GitOps manifest update changes production model version
  -> Argo CD syncs Kubernetes deployment
  -> FastAPI inference serves predictions
  -> Prometheus/Grafana/Loki/Evidently monitor service and model quality
```


## Модель і дані

Для фінального проєкту обрано Варіант B: публічний Iris dataset і модель LogisticRegression зі scikit-learn. Такий вибір зроблено свідомо: модель тренується за секунди, легко деплоїться як REST API, має зрозумілий JSON-вхід із чотирма числовими ознаками та підходить для демонстрації MLOps-платформи без зайвих витрат часу на ML-частину.

Вхід inference API:

```json
{
  "features": [5.1, 3.5, 1.4, 0.2]
}
```

Модель повертає class id і probabilities для трьох класів Iris.

## Namespace-и

```text
staging       - staging inference deployment для нових версій моделі
production    - production inference deployment
mlops-system  - Argo CD, MLflow, MinIO/PostgreSQL, service tooling
monitoring    - Prometheus, Grafana, Loki, PushGateway, Evidently CronJob
```


## Git repository structure decision

Для фінального проєкту обрано один Git repository, у якому разом зберігаються Terraform, application code, CI/CD конфігурації, документація та GitOps manifests у папці `gitops`. Це спрощує перевірку навчального проєкту: ментор бачить усю систему в одному місці, а bootstrap-процес не потребує синхронізації кількох repository.

У production-проєктах, які довго розвиваються, краще розділяти application/platform code і GitOps repository. Такий підхід зменшує ризик випадкових deploy-змін, дозволяє окремо керувати доступами до runtime-конфігурацій і робить promotion/rollback більш контрольованими. У цьому проєкті `gitops` виконує роль GitOps source всередині одного repository.
## Структура

```text

|-- terraform/
|   |-- vpc/
|   |-- eks/
|   |-- argocd/
|   |-- mlflow/
|   `-- monitoring/
|-- gitops/
|   |-- applications/
|   `-- manifests/
|-- apps/
|   |-- inference/
|   |-- training/
|   `-- evidently/
|-- rbac/
|-- docs/
|-- .github/workflows/
|-- README.md
|-- RUNBOOK.md
`-- ADR.md
```

## Залежності

- Terraform CLI >= 1.5
- AWS CLI з profile `default`
- kubectl
- Helm
- Docker або Podman
- Python 3.13
- GitHub Actions secrets для AWS-доступу

## Bootstrap з нуля

1. Створити/перевірити S3 bucket для Terraform state.
2. Підняти VPC:

```powershell
cd terraform/vpc
terraform init -backend-config backend.hcl
terraform plan
terraform apply
```

3. Підняти EKS:

```powershell
cd ../eks
terraform init -backend-config backend.hcl
terraform plan
terraform apply
aws eks --region eu-central-1 update-kubeconfig --name final-mlops-dev-eks --profile default
kubectl get nodes
```

4. Підняти Argo CD:

```powershell
cd ../argocd
terraform init -backend-config backend.hcl
terraform plan
terraform apply
```

5. Перед GitOps sync створити runtime secrets, які не зберігаються в Git:

```powershell
kubectl create namespace mlops-system --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
kubectl -n mlops-system create secret generic minio-credentials --from-literal=root-user=minioadmin --from-literal=root-password=minioadmin123
kubectl -n mlops-system create secret generic postgres-credentials --from-literal=POSTGRES_DB=mlflow --from-literal=POSTGRES_USER=mlflow --from-literal=POSTGRES_PASSWORD=mlflow123
kubectl -n monitoring create secret generic grafana-admin --from-literal=GF_SECURITY_ADMIN_USER=admin --from-literal=GF_SECURITY_ADMIN_PASSWORD=admin123
```

6. Після встановлення Argo CD застосувати root ApplicationSet:

```powershell
kubectl apply -f terraform/argocd/applicationset.yaml
```

ApplicationSet читає GitHub repository і створює Argo CD Applications для MLflow, monitoring, staging inference та production inference.

7. Перевірити статус:

```powershell
kubectl get applications -n mlops-system
kubectl get pods -n mlops-system
kubectl get pods -n monitoring
kubectl get pods -n staging
kubectl get pods -n production
```

## Port-forward

MLflow:

```powershell
kubectl -n mlops-system port-forward svc/mlflow 5000:5000
```

Grafana:

```powershell
kubectl -n monitoring port-forward svc/grafana 3000:80
```

Production inference:

```powershell
kubectl -n production port-forward svc/inference 8080:80
```

## Model Registry flow

Training pipeline реєструє модель у MLflow Model Registry з назвою `iris-classifier`. Нова версія переходить у Staging автоматично. Production promotion виконується вручну:

```powershell
python apps/training/promote_model.py --model-name iris-classifier --version <version> --stage Production
```

Rollback виконується так само, але з попередньою production-версією.

## Deployment strategy

Обрана Blue-Green стратегія: staging і production мають окремі namespace-и та окремі deployment-и. Нова модель перевіряється у staging, після promotion production manifest отримує нову model version/checksum. Для навчального проєкту це простіше, надійніше й легше демонструється, ніж canary.

## Security baseline

- Pydantic validation на `/predict`.
- Rate limiting у FastAPI middleware.
- RBAC roles у `rbac/`.
- Model artifact checksum SHA256 перед завантаженням моделі.
- Audit events для promotion/rollback у structured JSON logs.
- Threat model описаний у `docs/THREAT_MODEL.md`.

## Recommended blocks

- Evidently CronJob пише drift metrics у PushGateway/Prometheus.
- Grafana alerts описані у `gitops/manifests/monitoring/alerts.yaml`.
- Python tests, ruff/black, terraform fmt і Trivy workflow описані в CI.

## Destroy

Видаляти у зворотному порядку:

```powershell
kubectl delete -f terraform/argocd/applicationset.yaml --ignore-not-found
cd terraform/argocd
terraform destroy
cd ../eks
terraform destroy
cd ../vpc
terraform destroy
```


## Runtime secrets

Перед GitOps sync створити secrets командами з README bootstrap section.
