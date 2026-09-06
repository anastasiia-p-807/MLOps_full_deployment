from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1] / "rbac"


def documents(name):
    return list(yaml.safe_load_all((ROOT / name).read_text(encoding="utf-8")))


def allowed(role, verb, resource, group=""):
    return any(
        (verb in rule["verbs"] or "*" in rule["verbs"])
        and (resource in rule["resources"] or "*" in rule["resources"])
        and (group in rule["apiGroups"] or "*" in rule["apiGroups"])
        for rule in role["rules"]
    )


def test_engineer_namespace_boundary():
    roles = [doc for doc in documents("mlops-engineer.yaml") if doc["kind"] == "Role"]
    staging = next(role for role in roles if role["metadata"]["namespace"] == "staging")
    production = next(role for role in roles if role["metadata"]["namespace"] == "production")
    assert allowed(staging, "create", "deployments", "apps")
    assert allowed(staging, "delete", "secrets")
    assert allowed(production, "get", "pods")
    assert not allowed(production, "patch", "deployments", "apps")
    assert not allowed(production, "get", "secrets")


def test_viewer_has_no_write_or_secret_access():
    docs = documents("viewer.yaml")
    assert all(doc["kind"] in {"Role", "RoleBinding"} for doc in docs)
    for role in (doc for doc in docs if doc["kind"] == "Role"):
        assert allowed(role, "get", "pods")
        assert not allowed(role, "get", "secrets")
        assert not allowed(role, "delete", "pods")
        assert not allowed(role, "create", "pods/exec")
        assert all(set(rule["verbs"]) <= {"get", "list", "watch"} for rule in role["rules"])


def test_log_reader_is_namespaced_and_read_only():
    docs = documents("log-reader.yaml")
    assert not any(doc["kind"].startswith("Cluster") for doc in docs)
    for role in (doc for doc in docs if doc["kind"] == "Role"):
        assert allowed(role, "get", "pods/log")
        assert not allowed(role, "get", "secrets")
        assert not allowed(role, "get", "nodes/proxy")
        assert not allowed(role, "create", "pods/exec")


def test_user_roles_have_group_bindings():
    for filename, group in [("viewer.yaml", "viewer"), ("mlops-engineer.yaml", "mlops-engineer")]:
        docs = documents(filename)
        for role in (doc for doc in docs if doc["kind"] == "Role"):
            bindings = [
                doc
                for doc in docs
                if doc["kind"] == "RoleBinding"
                and doc["metadata"]["namespace"] == role["metadata"]["namespace"]
                and doc["roleRef"]["name"] == role["metadata"]["name"]
            ]
            assert len(bindings) == 1
            assert bindings[0]["subjects"][0]["name"] == group
