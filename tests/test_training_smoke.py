from sklearn.datasets import load_iris
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split


def test_training_smoke_on_small_sample():
    data = load_iris()
    x_train, x_test, y_train, y_test = train_test_split(
        data.data, data.target, test_size=0.25, random_state=42, stratify=data.target
    )
    model = LogisticRegression(max_iter=100, solver="lbfgs")
    model.fit(x_train, y_train)
    assert model.score(x_test, y_test) > 0.8
