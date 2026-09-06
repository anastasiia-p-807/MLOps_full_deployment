# Threat Model

## Attack surface

1. Inference API може отримати некоректний або шкідливий JSON input.
2. API може бути перевантажений великою кількістю запитів.
3. Model artifact у storage може бути підмінений.
4. Надмірні Kubernetes permissions можуть дозволити випадкову або зловмисну зміну production.
5. Model Registry actions можуть бути виконані без видимого audit trail.

## Controls

- Pydantic schema validation повертає HTTP 400 без внутрішніх деталей.
- Rate limiting обмежує кількість запитів на клієнта.
- Inference перевіряє SHA256 checksum перед завантаженням моделі.
- RBAC розділяє `mlops-engineer` і `viewer` ролі.
- Promotion/rollback пишуть structured audit logs, які збираються Loki.
