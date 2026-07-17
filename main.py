from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

import models
import database
from database import engine, get_db

# Создаем таблицы в БД (если они еще не созданы)
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# --- СХЕМЫ PYDANTIC ---

# Схема для валидации входящих данных при создании/обновлении (без ID)
class TaskSchema(BaseModel):
    title: str
    completed: bool = False

    class Config:
        from_attributes = True

# Схема для отдачи данных клиенту (с ID, сгенерированным базой данных)
class TaskResponse(BaseModel):
    id: int
    title: str
    completed: bool

    class Config:
        from_attributes = True


# --- МЕТОДЫ API (ЭНДПОИНТЫ) ---

# 1. Получение списка с возможностью фильтрации
@app.get("/tasks", response_model=List[TaskResponse])
def get_tasks(completed: Optional[bool] = None, db: Session = Depends(get_db)):
    query = db.query(models.TaskDB)
    if completed is not None:
        query = query.filter(models.TaskDB.completed == completed)
    return query.all()


# 2. Получение одной конкретной задачи по ID
@app.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task_by_id(task_id: int, db: Session = Depends(get_db)):
    task = db.query(models.TaskDB).filter(models.TaskDB.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return task


# 3. Добавление задачи (ID генерируется базой данных автоматически)
@app.post("/tasks", response_model=TaskResponse)
def add_task(task: TaskSchema, db: Session = Depends(get_db)):
    db_task = models.TaskDB(**task.model_dump())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


# 4. Удаление одной задачи по ID
@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(models.TaskDB).filter(models.TaskDB.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
    return {"message": "Удалено"}


# 5. Обновление (замена) задачи по ID
@app.put("/tasks/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, task_data: TaskSchema, db: Session = Depends(get_db)):
    task = db.query(models.TaskDB).filter(models.TaskDB.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    task.title = task_data.title
    task.completed = task_data.completed
    db.commit()
    db.refresh(task)
    return task


# 6. Удаление всех выполненных задач
@app.delete("/tasks/completed/")
def delete_completed_tasks(db: Session = Depends(get_db)):
    # Находим все выполненные задачи
    completed_query = db.query(models.TaskDB).filter(models.TaskDB.completed == True)
    removed_count = completed_query.count()
    
    # Удаляем их
    completed_query.delete(synchronize_session=False)
    db.commit()
    
    return {"message": f"Удалено {removed_count} выполненных задач"}


# 7. Поиск задач по текстовому запросу в названии
@app.get("/tasks/search/", response_model=List[TaskResponse])
def search_tasks(query: str, db: Session = Depends(get_db)):
    # Используем ilike для регистронезависимого поиска в SQLite
    return db.query(models.TaskDB).filter(models.TaskDB.title.ilike(f"%{query}%")).all()


# 8. Получение статистики
@app.get("/tasks/stats/")
def get_stats(db: Session = Depends(get_db)):
    total = db.query(models.TaskDB).count()
    completed = db.query(models.TaskDB).filter(models.TaskDB.completed == True).count()
    return {
        "total_tasks": total,
        "completed_tasks": completed,
        "percentage": (completed / total * 100) if total > 0 else 0
    }


# 9. Главная страница с веб-интерфейсом
@app.get("/", response_class=HTMLResponse)
def get_html():
    return """
    <html>
        <head>
            <style>
                body { font-family: 'Arial', sans-serif; background-color: #f4f4f9; padding: 50px; }
                h1 { color: #333; }
                input, select { padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
                button { padding: 10px 20px; background-color: #28a745; color: white; border: none; border-radius: 5px; cursor: pointer; }
                button:hover { background-color: #218838; }
                ul { list-style-type: none; padding: 0; }
                li { background: white; margin: 10px 0; padding: 15px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); display: flex; justify-content: space-between; align-items: center; }
                .btn-group { display: flex; gap: 5px; }
                .btn-danger { background-color: #dc3545; }
                .btn-danger:hover { background-color: #bd2130; }
                .btn-info { background-color: #17a2b8; }
                .btn-info:hover { background-color: #138496; }
            </style>
        </head>
        <body>
        <h1>Список моих задач (База Данных)</h1>

        <div style="display: flex; flex-direction: column; gap: 10px; width: 300px; margin-top: 20px;">
            <div style="display: flex; flex-direction: column; gap: 5px;">
                <!-- Убрали ручной ввод ID, так как база генерирует его сама! -->
                <input type="text" id="taskTitle" placeholder="Название новой задачи">
                <button onclick="addTask()">Добавить задачу</button>
            </div>

            <hr style="width: 100%;">

            <div style="display: flex; flex-direction: column; gap: 5px;">
                <input type="number" id="searchId" placeholder="Введите ID для поиска">
                <button onclick="searchTaskById()">Найти задачу по ID</button>
            </div>
            
            <div style="display: flex; flex-direction: column; gap: 5px;">
                <input type="text" id="searchText" placeholder="Поиск по тексту">
                <button onclick="searchTaskByText()">Найти по названию</button>
            </div>
        </div>

        <div id="stats" style="margin-top: 20px; padding: 10px; border: 1px dashed #aaa; width: 300px;">
            <button onclick="updateStats()">Обновить статистику</button>
            <p id="statsText">Нажмите кнопку для получения статистики</p>
        </div>

        <div style="margin: 20px 0; padding: 10px; background: #e9ecef; border-radius: 5px; width: 300px;">
            <label>Фильтр по статусу:</label>
            <select id="filterStatus" onchange="loadTasks()" style="padding: 5px; width: 100%;">
                <option value="all">Все задачи</option>
                <option value="true">Выполненные</option>
                <option value="false">В работе</option>
            </select>
        </div>

        <button onclick="deleteCompletedTasks()" class="btn-danger">
            Удалить выполненные
        </button>

        <div id="result" style="margin-top: 10px; font-weight: bold;"></div>

        <ul id="taskList"></ul>

        <script>
            // Добавление новой задачи (база данных сама выдаст ID)
            async function addTask() {
                const title = document.getElementById('taskTitle').value;
                if (!title) return alert("Введите название задачи!");

                await fetch('/tasks', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({title: title, completed: false})
                });
                document.getElementById('taskTitle').value = '';
                loadTasks(); 
                updateStats();
            }

            // Статистика
            async function updateStats() {
                const response = await fetch('/tasks/stats/');
                const data = await response.json();
                document.getElementById('statsText').textContent =
                `Всего задач: ${data.total_tasks}, Выполнено: ${data.completed_tasks} (${data.percentage.toFixed(0)}%)`;
            }

            // Загрузка списка (с фильтром или без)
            async function loadTasks() {
                const filter = document.getElementById('filterStatus').value;
                let url = (filter !== 'all') ? `/tasks?completed=${filter}` : '/tasks';

                const response = await fetch(url);
                const tasks = await response.json();

                const listElement = document.getElementById('taskList');
                listElement.innerHTML = ''; 

                tasks.forEach(task => {
                    const li = document.createElement('li');
                    
                    const spanText = document.createElement('span');
                    spanText.textContent = `[ID: ${task.id}] ${task.title} ${task.completed ? '✔ (Выполнено)' : '⏳ (В работе)'}`;
                    li.appendChild(spanText);

                    const btnGroup = document.createElement('div');
                    btnGroup.className = 'btn-group';

                    // Кнопка завершения (показывается только для невыполненных)
                    if (!task.completed) {
                        const completeBtn = document.createElement('button');
                        completeBtn.textContent = "✔ Решить";
                        completeBtn.onclick = () => completeTask(task.id, task.title);
                        btnGroup.appendChild(completeBtn);
                    }

                    // Кнопка удаления
                    const delBtn = document.createElement('button');
                    delBtn.textContent = "Удалить";
                    delBtn.className = 'btn-danger';
                    delBtn.onclick = () => deleteTask(task.id);
                    btnGroup.appendChild(delBtn);

                    li.appendChild(btnGroup);
                    listElement.appendChild(li);
                });
            }

            // Поиск задачи по конкретному ID
            async function searchTaskById() {
                const id = document.getElementById('searchId').value;
                const resultDiv = document.getElementById('result');
                if (!id) return alert("Введите ID для поиска!");

                const response = await fetch(`/tasks/${id}`);

                if (response.status === 404) {
                    resultDiv.textContent = "Ошибка: Задача с таким ID не найдена.";
                    resultDiv.style.color = "red";
                    return;
                }

                const task = await response.json();
                resultDiv.textContent = `ID ${task.id} Найдено: "${task.title}" (${task.completed ? 'Выполнено' : 'В работе'})`;
                resultDiv.style.color = "green";
            }

            // Поиск задач по совпадению текста в названии
            async function searchTaskByText() {
                const query = document.getElementById('searchText').value;
                if (!query) return alert("Введите текст для поиска!");
                
                const response = await fetch(`/tasks/search/?query=${query}`);
                const tasks = await response.json();
                
                const listElement = document.getElementById('taskList');
                listElement.innerHTML = ''; 
                
                if(tasks.length === 0) {
                    listElement.innerHTML = '<li>Ничего не найдено</li>';
                    return;
                }

                tasks.forEach(task => {
                    const li = document.createElement('li');
                    li.textContent = `[ID: ${task.id}] ${task.title} ${task.completed ? '✔' : '⏳'}`;
                    listElement.appendChild(li);
                });
            }

            // Удаление задачи
            async function deleteTask(id) {
                const response = await fetch(`/tasks/${id}`, { method: 'DELETE' });
                if (response.ok) {
                    loadTasks();
                    updateStats();
                }
            }

            // Изменение статуса задачи на "Выполнено" (PUT-запрос)
            async function completeTask(id, title) {
                const response = await fetch(`/tasks/${id}`, {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ title: title, completed: true })
                });

                if (response.ok) {
                    loadTasks();
                    updateStats();
                } else {
                    alert("Ошибка при обновлении задачи");
                }
            }

            // Очистка всех выполненных
            async function deleteCompletedTasks() {
                const response = await fetch('/tasks/completed/', { method: 'DELETE' });
                if (response.ok) {
                    loadTasks();
                    updateStats();
                }
            }

            // Инициализация страницы при загрузке
            loadTasks();
            updateStats();
        </script>
        </body>
    </html>
    """
