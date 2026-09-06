# RUNBOOK

## Контекст моделі

У проєкті використовується Iris dataset і LogisticRegression. Training має бути швидким: очікуваний час - секунди, не хвилини.

## Викотити нову версію моделі

1. Запустити training workflow у GitHub Actions або зробити push у main.
2. Перевірити новий run у MLflow.
3. Перевірити, що нова model version має stage `Staging`.
4. Протестувати staging inference endpoint.
5. Виконати promotion:

```powershell
python apps/training/promote_model.py --model-name iris-classifier --version <version> --stage Production
```

6. Оновити production manifest model version/checksum і зробити commit.
7. Перевірити Argo CD `Synced / Healthy`.

## Rollback

1. Знайти попередню production model version у MLflow.
2. Виконати promotion попередньої версії назад у Production.
3. Повернути production manifest на попередній model version/checksum одним commit.
4. Перевірити `/health` і `/predict`.

## Якщо Grafana показує latency p95 > 500ms

1. Перевірити CPU/RAM pod-ів inference.
2. Перевірити логи у Loki за `app=inference`.
3. Зменшити traffic або rollback на попередню model version.
4. Якщо проблема ресурсна - збільшити requests/limits або replicas.

## Якщо Evidently показує data drift

1. Перевірити drift dashboard.
2. Переглянути останні prediction samples.
3. Запустити training pipeline на оновленому dataset.
4. Не переводити модель у Production без manual approval.

## Видалити інфраструктуру

Виконати команди destroy з README у зворотному порядку: Applications, Argo CD, EKS, VPC.
