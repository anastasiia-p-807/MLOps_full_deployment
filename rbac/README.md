# Доступ до Kubernetes

## Користувацькі ролі

| Група Kubernetes | Namespace | Доступ |
| --- | --- | --- |
| mlops-engineer | staging | Усі дії над усіма namespaced ресурсами |
| mlops-engineer | production | Читання workloads, services, events та logs |
| viewer | staging, production, mlops-system, monitoring | Лише читання workloads, services, events та logs |

У production інженер не змінює Deployment вручну: promotion/deployment проходять через GitOps. Viewer не має доступу до Secrets, exec, port-forward, RBAC або зміни ресурсів. Повний staging-доступ інженера включає Secrets і локальний RBAC, але не дає cluster-wide прав.

RoleBinding прив'язує правила до груп `mlops-engineer` та `viewer`. Для реальних IAM principals ці групи потрібно вказати в EKS access entries. Поточний super-admin залишається адміністратором; додавання до обмеженої групи не скасовує його наявні права. Для демонстрації використовуємо impersonation груп від адміністратора.

## Розгортання через Git

Application `final-rbac` читає цю папку. Її manifest знаходиться у `gitops/manifests/monitoring/rbac-application.yaml`, тому її створює вже наявний Argo CD Application final-monitoring після Git push. Ручний kubectl apply для ролей не потрібен.

## Перевірка після Synced

Виконати як адміністратор; impersonation не створює користувачів:

```powershell
kubectl auth can-i create deployments -n staging --as=rbac-engineer-check --as-group=mlops-engineer
kubectl auth can-i get pods -n production --as=rbac-engineer-check --as-group=mlops-engineer
kubectl auth can-i patch deployments -n production --as=rbac-engineer-check --as-group=mlops-engineer
kubectl auth can-i get pods -n production --as=rbac-viewer-check --as-group=viewer
kubectl auth can-i delete pods -n staging --as=rbac-viewer-check --as-group=viewer
kubectl auth can-i get secrets -n production --as=rbac-viewer-check --as-group=viewer
```

Очікується: yes, yes, no, yes, no, no. Для can-i відповідь no повертає exit code 1, це очікуваний негативний тест.

## Технічна облікова запис

ServiceAccount `monitoring/log-reader` призначений для збору логів. Він може читати pod metadata і pod logs лише у staging, production та mlops-system. Не може читати Secrets, виконувати команди в контейнерах, змінювати workloads або звертатися до nodes/proxy. ClusterRole/ClusterRoleBinding для нього не створюються. Це не третя користувацька роль.

```powershell
kubectl auth can-i get pods --subresource=log -n production --as=system:serviceaccount:monitoring:log-reader
kubectl auth can-i get secrets -n production --as=system:serviceaccount:monitoring:log-reader
kubectl auth can-i get nodes --as=system:serviceaccount:monitoring:log-reader
```

Очікується: yes, no, no.
