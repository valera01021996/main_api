# Используем официальный образ Python 3.9
FROM python:3.10-slim

# Устанавливаем рабочую директорию в контейнере
WORKDIR /app

# Копируем файл requirements.txt в рабочую директорию
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект в рабочую директорию
COPY . .

# Открываем порт 5000 для доступа к приложению
EXPOSE 5000

# Запускаем приложение с использованием gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
