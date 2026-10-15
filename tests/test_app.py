import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'test.db'}")
    app.config["TESTING"] = True
    yield app.test_client()
    app.extensions["db_engine"].dispose()


@pytest.fixture
def student():
    return {"full_name": "Айдана Ермекова", "group_name": "ИС-22",
            "email": "aidana@example.test"}


def test_home(client):
    assert client.get("/").status_code == 200


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json["status"] == "ok"
    assert response.json["database"] == "sqlite"


def test_initial_list(client):
    assert client.get("/api/students").json == []


def test_create_and_read(client, student):
    response = client.post("/api/students", json=student)
    assert response.status_code == 201
    assert response.json["id"] > 0
    assert client.get(f"/api/students/{response.json['id']}").json["email"] == student["email"]
    assert len(client.get("/api/students").json) == 1


def test_update(client, student):
    student_id = client.post("/api/students", json=student).json["id"]
    student["group_name"] = "ИС-23"
    response = client.put(f"/api/students/{student_id}", json=student)
    assert response.status_code == 200
    assert response.json["group_name"] == "ИС-23"


def test_delete(client, student):
    student_id = client.post("/api/students", json=student).json["id"]
    assert client.delete(f"/api/students/{student_id}").status_code == 204
    assert client.get(f"/api/students/{student_id}").status_code == 404


def test_duplicate_email(client, student):
    assert client.post("/api/students", json=student).status_code == 201
    student["email"] = student["email"].upper()
    assert client.post("/api/students", json=student).status_code == 409


@pytest.mark.parametrize("changes", [
    {"full_name": " "}, {"group_name": ""}, {"email": "incorrect"},
    {"full_name": 123}, {"group_name": "x" * 31},
])
def test_invalid_fields(client, student, changes):
    student.update(changes)
    assert client.post("/api/students", json=student).status_code == 400


def test_invalid_json_type(client):
    assert client.post("/api/students", json=[1, 2]).status_code == 400


@pytest.mark.parametrize("method", ["get", "delete", "put"])
def test_missing_student(client, student, method):
    kwargs = {"json": student} if method == "put" else {}
    assert getattr(client, method)("/api/students/99999", **kwargs).status_code == 404
