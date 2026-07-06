import pytest
from fastapi.testclient import TestClient
from main import app, tasks  # Импортируем приложение и список задач

client = TestClient(app)

# Фикстура для сброса состояния списка перед каждым тестом
@pytest.fixture(autouse=True)
def reset_tasks():
    # Сохраняем начальное состояние
    original_tasks = tasks.copy()
    yield
    # Возвращаем список в исходное состояние после теста
    tasks.clear()
    tasks.extend(original_tasks)

def test_read_tasks():
    response = client.get("/tasks")
    assert response.status_code == 200
    assert len(response.json()) == 2

def test_add_task():
    payload = {"id": 3, "title": "Новая задача", "completed": False}
    response = client.post("/tasks", json=payload)
    assert response.status_code == 200
    assert response.json()["title"] == "Новая задача"
    
    # Проверяем, что задача реально добавилась
    get_response = client.get("/tasks/3")
    assert get_response.status_code == 200

def test_delete_task():
    # Удаляем задачу с id=1
    response = client.delete("/tasks/1")
    assert response.status_code == 200
    
    # Проверяем, что её больше нет
    get_response = client.get("/tasks/1")
    assert get_response.status_code == 404

def test_update_task():
    payload = {"id": 1, "title": "Измененная задача", "completed": True}
    response = client.put("/tasks/1", json=payload)
    assert response.status_code == 200
    assert response.json()["title"] == "Измененная задача"
    assert response.json()["completed"] is True

def test_search_tasks():
    response = client.get("/tasks/search/?query=верстку")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "Сделать верстку"

def test_get_stats():
    response = client.get("/tasks/stats/")
    assert response.status_code == 200
    data = response.json()
    assert data["total_tasks"] == 2
    assert data["completed_tasks"] == 1
    assert data["percentage"] == 50.0
def test_add_duplicate_task():
    # 1. Добавляем задачу
    payload = {"id": 10, "title": "Уникальная задача", "completed": False}
    client.post("/tasks", json=payload)
    
    # 2. Пытаемся добавить задачу с ТАКИМ ЖЕ ID
    duplicate_payload = {"id": 10, "title": "Дубликат", "completed": False}
    response = client.post("/tasks", json=duplicate_payload)
    
    # 3. Проверяем, что сервер вернул ошибку 400
    assert response.status_code == 400
    assert response.json()["detail"] == "Задача с таким ID уже существует"
def test_search_tasks_not_found():
    # 1. Делаем запрос к "/tasks/search/" с параметром query, 
    # которого точно нет в ваших задачах (например, "инопланетяне")
    response = client.get("/tasks/search/?query=инопланетяне") 
    
    # 2. Проверяем, что ответ успешный (статус 200)
    assert response.status_code == 200
    
    # 3. Проверяем, что вернулся именно пустой список
    assert response.json() == []
def test_delete_completed_tasks():
    # 1. Отправляем запрос на удаление
    response = client.delete("/tasks/completed/")
    assert response.status_code == 200
    
    # 2. Проверяем, что в списке не осталось выполненных задач
    remaining_tasks = client.get("/tasks").json()
    for task in remaining_tasks:
        assert task["completed"] is False
def test_add_task_invalid_data():
    # Отправляем задачу без обязательного поля title
    response = client.post("/tasks", json={"id": 4}) 
    assert response.status_code == 422  # Код ошибки валидации FastAPI

def test_delete_nonexistent_task():
    # Пытаемся удалить задачу, которой нет
    response = client.delete("/tasks/99999")
    assert response.status_code == 404
