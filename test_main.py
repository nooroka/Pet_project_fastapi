import pytest
from fastapi.testclient import TestClient
from main import app, tasks  # Импортируем приложение и список задач


# ==========================================
#              1. ФИКСТУРЫ
# ==========================================

@pytest.fixture
def api_client():
    """Создает изолированный веб-клиент для отправки HTTP-запросов."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_tasks():
    """Перед каждым тестом полностью очищает список задач, гарантируя изоляцию."""
    tasks.clear()
    yield
    tasks.clear()


@pytest.fixture
def valid_task_payload():
    """Возвращает корректные данные для создания новой задачи."""
    return {"id": 3, "title": "Новая задача", "completed": False}


@pytest.fixture
def duplicate_task_payload():
    """Возвращает данные задачи с ID=1 для проверки дубликатов."""
    return {"id": 1, "title": "Дубликат", "completed": False}


# ==========================================
#               2. ТЕСТЫ
# ==========================================

def test_read_tasks(api_client):
    """Проверяет получение списка всех задач."""
    # Сами наполняем базу перед проверкой
    api_client.post("/tasks", json={"id": 1, "title": "Задача 1", "completed": False})
    api_client.post("/tasks", json={"id": 2, "title": "Задача 2", "completed": True})

    response = api_client.get("/tasks")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_add_task(api_client, valid_task_payload):
    """Проверяет успешное создание новой задачи."""
    response = api_client.post("/tasks", json=valid_task_payload)
    assert response.status_code == 200
    assert response.json()["title"] == valid_task_payload["title"]

    # Проверяем, что задача реально доступна по её ID
    get_response = api_client.get(f"/tasks/{valid_task_payload['id']}")
    assert get_response.status_code == 200


def test_delete_task(api_client):
    """Проверяет удаление существующей задачи."""
    # Создаем задачу, которую будем удалять
    api_client.post("/tasks", json={"id": 1, "title": "Удаляемая задача", "completed": False})

    response = api_client.delete("/tasks/1")
    assert response.status_code == 200

    # Проверяем побочный эффект: задачи больше не должно быть
    get_response = api_client.get("/tasks/1")
    assert get_response.status_code == 404


def test_update_task(api_client):
    """Проверяет обновление данных задачи."""
    # Создаем задачу для обновления
    api_client.post("/tasks", json={"id": 1, "title": "Старая задача", "completed": False})

    payload = {"id": 1, "title": "Измененная задача", "completed": True}
    response = api_client.put("/tasks/1", json=payload)
    assert response.status_code == 200
    assert response.json()["title"] == "Измененная задача"
    assert response.json()["completed"] is True


def test_search_tasks(api_client):
    """Проверяет успешный поиск по ключевому слову."""
    api_client.post("/tasks", json={"id": 1, "title": "Сделать верстку", "completed": False})

    response = api_client.get("/tasks/search/?query=верстку")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "Сделать верстку"


def test_get_stats(api_client):
    """Проверяет расчет агрегированной статистики по задачам."""
    api_client.post("/tasks", json={"id": 1, "title": "Задача 1", "completed": True})
    api_client.post("/tasks", json={"id": 2, "title": "Задача 2", "completed": False})

    response = api_client.get("/tasks/stats/")
    assert response.status_code == 200
    data = response.json()
    assert data["total_tasks"] == 2
    assert data["completed_tasks"] == 1
    assert data["percentage"] == 50.0


def test_add_duplicate_task(api_client, duplicate_task_payload):
    """Проверяет ошибку при создании задачи с уже занятым ID."""
    # Создаем оригинальную задачу с ID=1
    api_client.post("/tasks", json={"id": 1, "title": "Оригинал", "completed": False})

    # Пробуем отправить дубликат с ID=1
    response = api_client.post("/tasks", json=duplicate_task_payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Задача с таким ID уже существует"


def test_search_tasks_not_found(api_client):
    """Проверяет, что при отсутствии совпадений в поиске возвращается пустой список."""
    response = api_client.get("/tasks/search/?query=инопланетяне")
    assert response.status_code == 200
    assert response.json() == []


def test_delete_completed_tasks(api_client):
    """Проверяет групповое удаление всех выполненных задач."""
    api_client.post("/tasks", json={"id": 1, "title": "Задача 1", "completed": True})
    api_client.post("/tasks", json={"id": 2, "title": "Задача 2", "completed": False})

    response = api_client.delete("/tasks/completed/")
    assert response.status_code == 200

    # Проверяем, что выполненная задача удалилась, а невыполненная осталась
    remaining_tasks = api_client.get("/tasks").json()
    for task in remaining_tasks:
        assert task["completed"] is False


def test_add_task_invalid_data(api_client):
    """Проверяет валидацию FastAPI при отправке некорректных данных (без title)."""
    response = api_client.post("/tasks", json={"id": 4})
    assert response.status_code == 422


def test_delete_nonexistent_task(api_client):
    """Проверяет ошибку при удалении задачи, которой нет в списке."""
    response = api_client.delete("/tasks/99999")
    assert response.status_code == 404


def test_update_nonexistent_task(api_client):
    """Проверяет ошибку при попытке обновить отсутствующую задачу."""
    payload = {"id": 999, "title": "Несуществующая", "completed": True}
    response = api_client.put("/tasks/999", json=payload)
    assert response.status_code == 404
    assert response.json()["detail"] == "Задача не найдена"

