import re
from typing import Optional


class Validators:
    @staticmethod
    def validate_github_url(url: str) -> bool:
        """Проверка валидности GitHub URL"""
        github_pattern = r'^https?://(www\.)?github\.com/[\w-]+/[\w-]+(/)?$'
        return bool(re.match(github_pattern, url))

    @staticmethod
    def sanitize_text(text: str, max_length: int = 1000) -> str:
        """Очистка и обрезка текста"""
        if not text:
            return ""
        # Удаляем лишние пробелы и специальные символы
        text = ' '.join(text.split())
        # Обрезаем до максимальной длины
        if len(text) > max_length:
            text = text[:max_length] + "..."
        return text

    @staticmethod
    def validate_subject(subject: str) -> Optional[str]:
        """Валидация названия предмета"""
        subjects = ['python', 'javascript', 'java', 'c++', 'sql', 'algorithms',
                    'web', 'mobile', 'devops', 'other']

        subject_lower = subject.lower()
        for valid_subject in subjects:
            if valid_subject in subject_lower:
                return valid_subject
        return 'other'


validators = Validators()