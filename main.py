from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from fastapi.responses import HTMLResponse

app = FastAPI()

class Task(BaseModel):
    id: int
    title: str
    completed: bool = False
tasks = [
    Task(id=1, title="Изучить FastAPI", completed=False),
    Task(id=2, title="Сделать верстку", completed=True)
]
# 1. Получение списка с возможностью фильтрации
@app.get("/tasks", response_model=List[Task])
def get_tasks(completed: Optional[bool] = None):
    # Если передан параметр ?completed=true/false, фильтруем список #этот параметр передается в javascript
    if completed is not None:
        return [t for t in tasks if t.completed == completed]
    return tasks
@app.get("/tasks/{task_id}", response_model=Task)
def get_task_by_id(task_id: int):
    for task in tasks:
        if task.id == task_id:
            return task
    # Если цикл завершился и мы не вернули задачу, значит её нет
    raise HTTPException(status_code=404, detail="Задача не найдена")

# 2. Добавление задачи
@app.post("/tasks", response_model=Task)
def add_task(task: Task):
    # Проверяем, есть ли уже задача с таким ID
    for existing_task in tasks:
        if existing_task.id == task.id:
            raise HTTPException(status_code=400, detail="Задача с таким ID уже существует")

    tasks.append(task)
    return task
# 3. Удаление задачи по ID
@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    # Ищем задачу с нужным ID
    for index, task in enumerate(tasks):
        if task.id == task_id:
             tasks.pop(index) # Удаляем и возвращаем удаленную задачу
             return {"message": "Задача успешно удалена"}
        raise HTTPException(status_code=404, detail="Task not found")
    # Если цикл закончился и мы ничего не нашли — ошибка 404
@app.put("/tasks/{task_id}", response_model=Task)

def replace_task(task_id: int, updated_task: Task):
    for index, task in enumerate(tasks):
        if task.id == task_id:
            # Принудительно сохраняем ID из пути, чтобы пользователь не мог его изменить
            updated_task.id = task_id 
            tasks[index] = updated_task
            return updated_task
    raise HTTPException(status_code=404, detail="Задача не найдена")
@app.delete("/tasks/completed/")
def delete_completed_tasks():
    global tasks
    # Оставляем только те задачи, которые НЕ выполнены
    initial_count = len(tasks)
    tasks = [t for t in tasks if not t.completed]
    removed_count = initial_count - len(tasks)

    return {"message": f"Удалено {removed_count} выполненных задач"}
@app.get("/tasks/search/")
def search_tasks(query: str):
    return [t for t in tasks if query.lower() in t.title.lower()]

# 5. Получение статистики
@app.get("/tasks/stats/")
def get_stats():
    total = len(tasks)
    completed = len([t for t in tasks if t.completed])
    return {
        "total_tasks": total,
        "completed_tasks": completed,
        "percentage": (completed / total * 100) if total > 0 else 0
    }
@app.get("/", response_class=HTMLResponse)
def get_html():
    return """
    <html>
        <head>
            <style>
                /* Стили для всей страницы */
                body { font-family: 'Arial', sans-serif; background-color: #f4f4f9; padding: 50px; }
                h1 { color: #333; }
                
                /* Стили для формы */
                input { padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
                button { padding: 10px 20px; background-color: #28a745; color: white; border: none; border-radius: 5px; cursor: pointer; }
                button:hover { background-color: #218838; }

                /* Стили для списка */
                ul { list-style-type: none; padding: 0; }
                li { background: white; margin: 10px 0; padding: 15px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            </style>
        </head>
        <body>
        <h1>Список моих задач</h1>

        <div style="display: flex; flex-direction: column; gap: 10px; width: 300px; margin-top: 20px;">
        <div style="display: flex; flex-direction: column; gap: 5px;">
            <input type="number" id="taskId" placeholder="ID (число)">
            <input type="text" id="taskTitle" placeholder="Название задачи">
            <button onclick="addTask()">Добавить задачу</button>
        </div>

        <hr style="width: 100%;">

        <div style="display: flex; flex-direction: column; gap: 5px;">
            <input type="number" id="searchId" placeholder="Введите ID для поиска">
            <button onclick="searchTask()">Найти задачу</button>
        </div>
    </div>
    <div id="stats" style="margin-top: 20px; padding: 10px; border: 1px dashed #aaa;">
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
    <button onclick="deleteCompletedTasks()" style="background-color: #dc3545; color: white;">
    Удалить выполненные
    </button>
    <div id="result" style="margin-top: 10px; font-weight: bold;"></div>

           <ul id="taskList"></ul>

            <script>
                async function addTask() {
                    const id = document.getElementById('taskId').value;
                    const title = document.getElementById('taskTitle').value;
                    
                    if (!id || !title) return alert("Введите ID и Название!");

                    await fetch('/tasks', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({id: parseInt(id), title: title, completed: false})
                    });
                    loadTasks(); 
                }
                async function updateStats() {
                const response = await fetch('/tasks/stats/');
                const data = await response.json();
                document.getElementById('statsText').textContent =
                `Всего задач: ${data.total_tasks}, Выполнено: ${data.completed_tasks} (${data.percentage.toFixed(0)}%)`;
                }
                async function loadTasks() {
                const filter = document.getElementById('filterStatus').value;
                let url = (filter !== 'all') ? `/tasks?completed=${filter}` : '/tasks';

                const response = await fetch(url);
                const tasks = await response.json();

                const listElement = document.getElementById('taskList');
                listElement.innerHTML = ''; // ОЧИЩАЕМ СПИСОК ПЕРЕД ОТРИСОВКОЙ

                tasks.forEach(task => {
                const li = document.createElement('li');
                li.textContent = `${task.title} ${task.completed ? '(Выполнено)' : '(В работе)'} `;

                // Кнопка удаления
                const delBtn = document.createElement('button');
                delBtn.textContent = "Удалить";
                delBtn.onclick = () => deleteTask(task.id);
                li.appendChild(delBtn);

                // Кнопка завершения (если нужно)
                if (!task.completed) {
                    const completeBtn = document.createElement('button');
                    completeBtn.textContent = "✔";
                    completeBtn.onclick = () => completeTask(task.id, task.title);
                    li.appendChild(completeBtn);
                }

                listElement.appendChild(li);
                });
                }
                async function showTaskDetails(id) {
                const response = await fetch(`/tasks/${id}`); // Вот здесь мы используем ваш новый метод
                const task = await response.json();

                const detailsDiv = document.getElementById('details');
                const detailsText = document.getElementById('detailsText');

                detailsDiv.style.display = 'block';
                detailsText.textContent = `Название: ${task.title}, Статус: ${task.completed ? 'Выполнено' : 'В работе'}`;
                }
                async function searchTask() {
                const id = document.getElementById('searchId').value; // ID, который ввел пользователь
                const resultDiv = document.getElementById('result');  // Блок для вывода результата

                try {
                const response = await fetch(`/tasks/${id}`);

                // Проверяем, успешен ли ответ
                if (response.status === 404) {
                        resultDiv.textContent = "Ошибка: Задача не найдена.";
                        resultDiv.style.color = "red";
                        return;
                }

                const task = await response.json();
                resultDiv.textContent = `Найдено: ${task.title}`;
                resultDiv.style.color = "green";

                } catch (error) {
                resultDiv.textContent = "Произошла ошибка соединения с сервером.";
                }
                }
                async function deleteTask(id) {
                console.log("Пытаюсь удалить ID:", id); // Добавьте этот лог для отладки
                const response = await fetch(`/tasks/${id}`, {
                method: 'DELETE'
                });

                if (response.ok) {
                    console.log("Удалено успешно!");
                    loadTasks(); // Обновляем список
                } else {
                console.error("Ошибка при удалении:", response.status);
                 }
                }
                async function completeTask(id, title) {
                const response = await fetch(`/tasks/${id}`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                id: id,
                title: title,
                completed: true // Устанавливаем статус "выполнено"
                })
                });

                if (response.ok) {
                    loadTasks(); // Перезагружаем список, чтобы увидеть статус (Выполнено)
                 } else {
                alert("Ошибка при обновлении задачи");
                 }
                }
                async function deleteCompletedTasks() {
                const response = await fetch('/tasks/completed/', {
                method: 'DELETE'
                });

                if (response.ok) {
                console.log("Выполненные задачи успешно удалены");
                loadTasks();      // Перерисовываем список
                updateStats();    // Обновляем статистику
                } else {
                    alert("Не удалось удалить задачи");
                }
                }
                loadTasks();
            </script>
        </body>
    </html>
    """
