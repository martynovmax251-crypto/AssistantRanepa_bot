-- Создание базы данных
CREATE DATABASE IF NOT EXISTS it_student_db
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE it_student_db;

-- Таблица пользователей
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    registered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_active DATETIME,
    settings JSON DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Таблица ошибок (Error Log)
CREATE TABLE error_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    error_text TEXT NOT NULL,
    subject VARCHAR(255),
    solution_text TEXT,
    screenshot_path VARCHAR(512),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    solved_at DATETIME,
    next_review DATETIME,
    review_count INT DEFAULT 0,
    is_resolved BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    INDEX idx_user_review (user_id, next_review),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Таблица карточек (Flashcards)
CREATE TABLE flashcards (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    category VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    ease_factor FLOAT DEFAULT 2.5,
    interval_days INT DEFAULT 0,
    repetitions INT DEFAULT 0,
    next_review DATETIME,
    last_reviewed DATETIME,
    total_reviews INT DEFAULT 0,
    correct_reviews INT DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    INDEX idx_next_review (next_review)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Таблица Pomodoro сессий
CREATE TABLE pomodoro_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    topic VARCHAR(255),
    duration_minutes INT,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    status ENUM('active', 'completed', 'interrupted') DEFAULT 'active',
    github_commit_url VARCHAR(512),
    notes TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    INDEX idx_user_date (user_id, started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Таблица идей проектов
CREATE TABLE project_ideas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    difficulty ENUM('beginner', 'intermediate', 'advanced') DEFAULT 'beginner',
    technologies VARCHAR(512),
    created_by BIGINT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (created_by) REFERENCES users(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Таблица статистики повторений
CREATE TABLE review_statistics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    item_type ENUM('error', 'flashcard') NOT NULL,
    item_id INT NOT NULL,
    reviewed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    was_correct BOOLEAN,
    response_time_ms INT,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Начальные данные для идей проектов
INSERT INTO project_ideas (title, description, difficulty, technologies) VALUES
('Система учета личных финансов', 'Создайте приложение для отслеживания доходов и расходов с визуализацией данных', 'beginner', 'Python, SQLite, Matplotlib'),
('Telegram бот для изучения языков', 'Бот с карточками слов, тестами и статистикой прогресса', 'intermediate', 'Python, aiogram, PostgreSQL'),
('Визуализатор алгоритмов сортировки', 'Веб-приложение, показывающее работу разных алгоритмов сортировки', 'intermediate', 'JavaScript, React, Canvas'),
('Менеджер паролей', 'Безопасное хранилище паролей с шифрованием', 'advanced', 'Python, Cryptography, SQLite'),
('Система мониторинга сервера', 'Сбор метрик системы и отправка уведомлений в Telegram', 'intermediate', 'Python, psutil, aiogram'),
('Генератор резюме', 'Сервис для создания красивых резюме из шаблонов', 'beginner', 'Python, Jinja2, PDF generation'),
('Планировщик задач с Pomodoro', 'Таск-менеджер со встроенным Pomodoro таймером', 'intermediate', 'Python, Tkinter/PyQt, SQLite');