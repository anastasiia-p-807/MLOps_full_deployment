# Final Project: MLOps platform в AWS

Проєкт об'єднує EKS, Argo CD, MLflow Model Registry, inference API та моніторинг. Перевірено ручне навчання моделі, promotion у Production та розгортання образу через GitOps.

## Scope

Нижче описано виконані кроки та перевірені результати. Незавершені частини винесено до розділу «Подальші покращення»; частина з них належить до обов'язкових вимог завдання. Основний сценарій - AWS/EKS, без локального fallback та бонусних завдань.

## Доступ для перевірки

Результати роботи показано на скріншотах у `Screenshots/`. Для перевірки production inference створено окремий Service `inference-public` типу `LoadBalancer` (AWS NLB). UI Grafana, MLflow та MinIO залишаються доступними лише через `kubectl port-forward`; їхні посилання `localhost` не доступні з іншого комп'ютера.

Публічний API: [health](http://a5fa5ba1610334c45b5619071d63f630-1b3a1daa13299a81.elb.eu-central-1.amazonaws.com/health), [Swagger UI](http://a5fa5ba1610334c45b5619071d63f630-1b3a1daa13299a81.elb.eu-central-1.amazonaws.com/docs). У Swagger вибрати `POST /predict`, натиснути `Try it out` та передати `{"features": [5.1, 3.5, 1.4, 0.2]}`.

Це тимчасовий навчальний HTTP endpoint без TLS та авторизації; відкрито також `/metrics`. Не передавати секрети або персональні дані. Адреса працює, поки існують кластер і балансировщик. NLB платний; після перевірки його потрібно видалити разом із сервісом. Манифест: `gitops/manifests/inference/production/public-service.yaml`.

Незавершені пункти, зокрема частину обов'язкових вимог, перелічено в розділі «Подальші покращення». Їх не подано як виконані.

## Архітектура

```text
Ручний запуск train_register.py -> MLflow Registry (Staging)
  -> завантаження model.joblib -> Podman build -> Amazon ECR
  -> GitHub manifests -> Argo CD -> staging inference
  -> ручний promotion у MLflow -> production manifest -> production inference

Inference /metrics -> Prometheus -> Grafana
Inference JSON logs -> Alloy -> Loki -> Grafana
Evidently CronJob (iris_demo) -> PushGateway -> Prometheus -> Grafana alerts
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
monitoring    - Prometheus, Grafana, Loki, Alloy, PushGateway, Evidently CronJob
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
- Podman
- Python 3.13

## Виконане розгортання

1. Використано S3 bucket `s3-terraform-bucket-mlops`, регіон `eu-central-1`, AWS profile `default`. У `vpc/`, `eks/`, `argocd/` підготовлено локальні `backend.hcl` і `terraform.tfvars`; state keys мають префікс `final/`.
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

5. Перед GitOps sync створено runtime secrets з окремими випадковими паролями. Вони зберігаються у Kubernetes, а не в Git. Перевірка наявності:

```powershell
kubectl -n mlops-system get secrets minio-credentials postgres-credentials
kubectl -n monitoring get secret grafana-admin
```

6. Після встановлення Argo CD застосовано root ApplicationSet з кореня репозиторію:

```powershell
kubectl apply -f terraform/argocd/applicationset.yaml
```

ApplicationSet читає GitHub repository і створює Argo CD Applications для MLflow, monitoring, staging inference та production inference. Дочірня Application `final-rbac` застосовує ролі з папки `rbac/`.

У EKS працюють два CPU-узли: один вузол досяг ліміту кількості pod-ів. MinIO/PostgreSQL використовують `emptyDir`; їхні дані не зберігаються після заміни pod-а.

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

Скрипт `train_register.py` було запущено вручну. Він зареєстрував `iris-classifier`, версію `1`, зі стадією Staging. Виконано promotion:

```powershell
.\.venv\Scripts\python.exe apps/training/promote_model.py --model-name iris-classifier --version 1 --stage Production
```

Перевірений run ID: `e1fcd92b3cb34612b72fccc34c082978`. Образ `final-inference:e1fcd92b3cb3` опубліковано в ECR. SHA256 локального `model.joblib` збігається зі значенням у MLflow.

## Перевірка inference

Staging і production мають окремі namespace-и та Deployment-и. Після перевірки staging оновлено production manifest і дочекалися синхронізації Argo CD. Це звичайний rollout; Blue-Green перемикач трафіку не реалізовано.

Для входу `[5.1, 3.5, 1.4, 0.2]` production API повернув `prediction: 0`, ймовірність близько `0.9864` та `model_version: 1`. `/health` повернув `status: ok`.

## Автоматичне навчання

`Final training pipeline`: тести -> Lambda `ValidateInput` -> Step Functions `TrainAndRegister` -> EKS Job -> MLflow Registry (`Staging`). Production не змінюється. Job завантажує training script і залежності з конкретного Git SHA цього публічного репозиторію. Метрики, dataset version, SHA та checksum зберігаються у MLflow. GitHub очікує завершення Step Functions; помилка Job означає помилку workflow.

Одноразове налаштування з кореня репозиторію після розгортання MLflow:

```powershell
Copy-Item terraform/training/backend.hcl.example terraform/training/backend.hcl
terraform -chdir=terraform/training init -backend-config backend.hcl
terraform -chdir=terraform/training validate
terraform -chdir=terraform/training plan -out training.tfplan
terraform -chdir=terraform/training apply training.tfplan
```

Додати `rbac/training-runner.yaml` у Git; Argo CD Application `final-rbac` створить namespace `mlops-training` та права оркестратора. Після синхронізації:

```powershell
kubectl get ns mlops-training
.\.venv\Scripts\python.exe apps/training/prepare_runtime_secret.py
```

Runtime secret копіюється з наявного MinIO secret без виведення значень і без запису у Git або Terraform state. У навчальному варіанті використано ті самі MinIO credentials; окремий користувач із bucket-scoped policy залишається покращенням. ServiceAccount Job не має Kubernetes API token; IAM-роль оркестратора має права на Jobs і читання логів лише в `mlops-training`, не в production.

У GitHub потрібні secrets `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION=eu-central-1`. `AWS_STEP_FUNCTION_ARN` більше не потрібний: ARN `final-mlops-training` визначається для поточного AWS-аккаунта. CI-користувачу потрібні `states:DescribeStateMachine`, `states:StartExecution` для цієї state machine, `states:DescribeExecution` і `states:StopExecution` для її executions.

Після push змін коду або ручного `Run workflow` перевірити Step Functions -> `final-mlops-training`, Job `iris-train-*` у `mlops-training` та нову версію `iris-classifier` у Staging. Встановлення залежностей займає довше, ніж саме навчання; Job обмежено 25 хвилинами, workflow Step Functions - 30 хвилинами. Job видаляється через добу після завершення. При скасуванні CI перевірити execution/Job: скасування GitHub не гарантує зупинку Job.

AWS-ресурси створено через Terraform. Наскрізний запуск перевіряється окремо; наявність state machine сама по собі не означає успішне навчання.

## Безпека та перевірки

- **F1:** інтеграційний тест запускає справжній `train_register.py` двічі з ізольованою SQLite-базою MLflow, перевіряє метрики, реєстрацію версій у Staging, теги та checksum завантаженого `model.joblib`, а також передбачення з нього. Тест пройшов локально; AWS не використовується. Наявні workflows запускають його через `pytest tests`; результат нового запуску GitHub Actions ще не перевірено.

- Перевірено SHA256 моделі під час запуску контейнера.
- RBAC застосовано через Argo CD: `mlops-engineer` має повний доступ до staging та читання production; `viewer` - лише читання без Secrets. Дозволи та заборони перевірено через `kubectl auth can-i`; опис у `rbac/README.md`.
- Alloy читає pod logs через окремий ServiceAccount з namespaced правами, без ClusterRole та доступу до Secrets.
- Локально пройшли 13 training/inference/RBAC тестів і 3 drift-тести, Ruff, Black та Terraform fmt. HTTP 400/429 перевірено тестами оновленого коду; цей код ще потрібно включити в новий образ і перевірити в EKS.
- Скрипт promotion вивів структуровану подію переходу моделі в Production у термінал. Доставку Registry audit у Loki ще не реалізовано.
- Threat model описано у `docs/THREAT_MODEL.md`.

## Моніторинг

- У Grafana Explore перевірено запити, передбачення та latency inference API.
- У Loki отримано структуровані production-логи `{"event":"prediction","prediction":0}` через Alloy.
- Evidently CronJob успішно виконав контрольні сценарії Iris: `baseline=0`, `shifted=0.5`. Це drift на тестових даних, а не на поточних production-передбаченнях.
- Grafana завантажує правила latency p95 > 500 ms, HTTP 5xx > 1%, недоступності inference та demo drift > 0.2. Для `shifted` підтверджено Firing, для `baseline` - Normal.

Запити для перевірки:

```promql
evidently_drift_score{source="iris_demo"}
```

```logql
{namespace="production",app="inference"} | json | event="prediction"
```

## Подальші покращення

Нижче наведено незавершені роботи, а не підтверджені результати. Обов'язкові пункти позначено номерами завдання.

- **A1, A3, D:** завершити відтворюваний bootstrap без неописаних ручних кроків та узгодити README, RUNBOOK і ADR з остаточною реалізацією.
- **A5:** створити Grafana dashboard з CPU/RAM pod-ів, request rate, p50/p95 latency та error rate.
- **B1:** завершити автоматичне навчання через GitHub Actions і AWS Step Functions. Workflow-файли є, але успішний наскрізний CI запуск не підтверджено.
- **B3, B4:** реалізувати Blue-Green переключення та продемонструвати rollback. Rollback у цьому проході пропущено.
- **C1, C2:** зібрати оновлений inference-образ і перевірити HTTP 400/429 у кластері.
- **C5:** надсилати аудит операцій Model Registry у Loki.
- **E1, E3:** обчислювати drift за реальними production-передбаченнями та описати escalation policy і contact points.
- **F2-F3:** перевірити lint/hooks і сканування саме контейнерного образу в CI. Наявний Trivy workflow сканує файли репозиторію.
- Перейти від `emptyDir` до постійного сховища для metadata та artifacts MLflow.

## Destroy

Після завершення перевірок видалити ресурси у зворотному порядку. Ці команди наведено для майбутнього очищення; фінальний destroy ще не підтверджено. Починати з кореня репозиторію та дочекатися видалення дочірніх Applications до зупинки Argo CD:

```powershell
kubectl delete -f terraform/argocd/applicationset.yaml --ignore-not-found --wait=true --timeout=300s
kubectl get applications -n mlops-system
kubectl delete svc inference-public -n production --ignore-not-found --wait=true --timeout=300s
terraform -chdir=terraform/training destroy
cd terraform/argocd
terraform destroy
cd ../eks
terraform destroy
cd ../vpc
terraform destroy
```


