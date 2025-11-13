# 🔌 API Examples

Примеры использования API для тестирования и интеграции.

## Переменные окружения для примеров

```bash
export API_URL="http://localhost:8000"
export SECRET="mvp-secret-key-2024-xyz"
```

## Health Check

Проверка работоспособности сервиса:

```bash
curl $API_URL/health
```

**Ответ:**
```json
{
  "status": "ok",
  "service": "fb-job-parser"
}
```

## Получение списка вакансий

### Получить последние 50 вакансий

```bash
curl "$API_URL/api/jobs?limit=50&offset=0"
```

### Получить следующие 50 вакансий

```bash
curl "$API_URL/api/jobs?limit=50&offset=50"
```

**Ответ:**
```json
{
  "jobs": [
    {
      "id": 1,
      "group_name": "[FACEBOOK] ProjectAmazon",
      "text": "Ищем Python разработчика...",
      "link": "https://facebook.com/123456",
      "created_at": "2024-11-13 10:30:00"
    }
  ],
  "total": 150
}
```

## Управление Facebook группами

### Получить список групп

```bash
curl "$API_URL/api/groups"
```

**Ответ:**
```json
{
  "groups": [
    {
      "id": 1,
      "group_id": "ProjectAmazon",
      "group_name": "Project Amazon Jobs",
      "enabled": true,
      "added_at": "2024-11-13 09:00:00"
    }
  ]
}
```

### Добавить новую группу

```bash
curl -X POST "$API_URL/api/groups" \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "TechJobsRussia",
    "group_name": "Tech Jobs Russia"
  }'
```

**Ответ:**
```json
{
  "status": "success",
  "group": {
    "id": 2,
    "group_id": "TechJobsRussia",
    "group_name": "Tech Jobs Russia"
  }
}
```

### Добавить группу по URL

```bash
curl -X POST "$API_URL/api/groups" \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "https://facebook.com/groups/TechJobsRussia",
    "group_name": "Tech Jobs"
  }'
```

### Включить/отключить группу

```bash
# Переключить статус группы с ID=1
curl -X POST "$API_URL/api/groups/1/toggle"
```

**Ответ:**
```json
{
  "status": "success",
  "enabled": false
}
```

### Удалить группу

```bash
curl -X DELETE "$API_URL/api/groups/1"
```

**Ответ:**
```json
{
  "status": "success"
}
```

## Отправка вакансии (для парсера)

Этот endpoint используется парсером для отправки найденных вакансий:

```bash
curl -X POST "$API_URL/post" \
  -H "Content-Type: application/json" \
  -H "X-SECRET: $SECRET" \
  -d '{
    "chat_title": "[FACEBOOK] ProjectAmazon",
    "text": "Требуется Python разработчик с опытом в Django...",
    "link": "https://facebook.com/123456789",
    "source_type": "facebook"
  }'
```

**Ответ (успех):**
```json
{
  "status": "success"
}
```

**Ответ (дубликат):**
```json
{
  "status": "duplicate",
  "message": "Job already exists"
}
```

**Ответ (ошибка авторизации):**
```json
{
  "error": "Unauthorized"
}
```

## JavaScript примеры

### Получение вакансий

```javascript
async function getJobs(limit = 50, offset = 0) {
  const response = await fetch(
    `${API_URL}/api/jobs?limit=${limit}&offset=${offset}`
  );
  const data = await response.json();
  return data;
}

// Использование
const jobs = await getJobs();
console.log(`Всего вакансий: ${jobs.total}`);
jobs.jobs.forEach(job => {
  console.log(`${job.group_name}: ${job.text.substring(0, 50)}...`);
});
```

### Добавление группы

```javascript
async function addGroup(groupId, groupName) {
  const response = await fetch(`${API_URL}/api/groups`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      group_id: groupId,
      group_name: groupName
    })
  });
  
  if (response.ok) {
    const data = await response.json();
    console.log('Группа добавлена:', data.group);
    return data;
  } else {
    const error = await response.json();
    console.error('Ошибка:', error.error);
    throw new Error(error.error);
  }
}

// Использование
await addGroup('ProjectAmazon', 'Project Amazon Jobs');
```

### Переключение группы

```javascript
async function toggleGroup(groupId) {
  const response = await fetch(
    `${API_URL}/api/groups/${groupId}/toggle`,
    { method: 'POST' }
  );
  const data = await response.json();
  console.log(`Группа ${data.enabled ? 'включена' : 'отключена'}`);
  return data;
}

// Использование
await toggleGroup(1);
```

## Python примеры

### Получение вакансий

```python
import requests

def get_jobs(api_url, limit=50, offset=0):
    response = requests.get(
        f"{api_url}/api/jobs",
        params={"limit": limit, "offset": offset}
    )
    return response.json()

# Использование
jobs = get_jobs("http://localhost:8000")
print(f"Всего вакансий: {jobs['total']}")
for job in jobs['jobs']:
    print(f"{job['group_name']}: {job['text'][:50]}...")
```

### Добавление группы

```python
import requests

def add_group(api_url, group_id, group_name):
    response = requests.post(
        f"{api_url}/api/groups",
        json={
            "group_id": group_id,
            "group_name": group_name
        }
    )
    
    if response.ok:
        data = response.json()
        print(f"Группа добавлена: {data['group']}")
        return data
    else:
        error = response.json()
        print(f"Ошибка: {error['error']}")
        raise Exception(error['error'])

# Использование
add_group("http://localhost:8000", "ProjectAmazon", "Project Amazon Jobs")
```

### Отправка вакансии

```python
import requests

def send_job(api_url, secret, group_name, text, link=None):
    response = requests.post(
        f"{api_url}/post",
        headers={
            "X-SECRET": secret,
            "Content-Type": "application/json"
        },
        json={
            "chat_title": f"[FACEBOOK] {group_name}",
            "text": text,
            "link": link,
            "source_type": "facebook"
        }
    )
    return response.json()

# Использование
result = send_job(
    "http://localhost:8000",
    "mvp-secret-key-2024-xyz",
    "ProjectAmazon",
    "Требуется Python разработчик...",
    "https://facebook.com/123456"
)
print(result)
```

## Коды ответов

- `200` - Успешный запрос
- `401` - Неавторизован (неверный secret)
- `404` - Не найдено
- `409` - Конфликт (дубликат)
- `500` - Внутренняя ошибка сервера

## Примеры ошибок

### Группа уже существует

```json
{
  "error": "Group already exists"
}
```

### Группа не найдена

```json
{
  "error": "Group not found"
}
```

### Неверный запрос

```json
{
  "error": "Group ID is required"
}
```

## Тестирование с помощью Postman

1. Импортируйте Collection:

```json
{
  "info": {
    "name": "Facebook Job Parser API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Health Check",
      "request": {
        "method": "GET",
        "url": "{{api_url}}/health"
      }
    },
    {
      "name": "Get Jobs",
      "request": {
        "method": "GET",
        "url": "{{api_url}}/api/jobs?limit=50&offset=0"
      }
    },
    {
      "name": "Get Groups",
      "request": {
        "method": "GET",
        "url": "{{api_url}}/api/groups"
      }
    },
    {
      "name": "Add Group",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"group_id\": \"ProjectAmazon\",\n  \"group_name\": \"Project Amazon Jobs\"\n}"
        },
        "url": "{{api_url}}/api/groups"
      }
    }
  ]
}
```

2. Создайте Environment с переменной `api_url`

---

**Полезные ссылки:**
- [Flask документация](https://flask.palletsprojects.com/)
- [python-telegram-bot документация](https://docs.python-telegram-bot.org/)
- [facebook-scraper документация](https://github.com/kevinzg/facebook-scraper)
