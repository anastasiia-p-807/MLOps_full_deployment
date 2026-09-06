# ADR: Deployment strategy and platform design

## Рішення

Для фінального проєкту обрана Blue-Green deployment strategy. Staging і production працюють як окремі Kubernetes namespace-и з окремими deployment-ами inference-сервісу.

## Чому Blue-Green

Canary краще для поступового rollout, але потребує стабільного traffic splitting через Ingress/service mesh. Для навчального AWS/EKS стенду Blue-Green простіший, прозоріший і краще підходить для демонстрації: staging перевіряє нову модель, production перемикається тільки після promotion у MLflow Registry.

## Trade-offs

Переваги:

- простий rollback;
- чітке розділення staging/production;
- менше мережевої складності;
- легко показати ментору через Argo CD і MLflow.

Недоліки:

- потрібно підтримувати дві копії deployment;
- немає плавного 90/10 traffic split;
- потрібно уважно синхронізувати model version і checksum.

## Що зробити інакше за більшого часу

- Додати canary rollout через Argo Rollouts.
- Додати OIDC для CI замість static AWS keys.
- Перенести secrets у AWS Secrets Manager або External Secrets Operator.
- Додати OpenTelemetry tracing.

## Вибір моделі та датасету

Обрано Варіант B: публічний Iris dataset і LogisticRegression зі scikit-learn. Мета фінального проєкту - показати production-ready MLOps platform, а не складну ML-модель, тому простий класифікатор є кращим інженерним вибором.

Переваги цього вибору:

- тренування займає секунди, значно менше за ліміт 30 хвилин;
- модель легко серіалізується і деплоїться як REST API;
- JSON input простий: чотири числові ознаки;
- dataset стабільний і підходить для reference dataset у drift checks;
- такий самий підхід уже був перевірений у lesson-9 з MLflow metrics.
