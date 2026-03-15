import pytesseract
from PIL import Image
import io
import logging
from config import config

logger = logging.getLogger(__name__)


class OCRHelper:
    @staticmethod
    async def extract_text_from_image(image_bytes: bytes) -> str:
        """Извлечение текста из изображения"""
        try:
            # Открываем изображение из байтов
            image = Image.open(io.BytesIO(image_bytes))

            # Распознаем текст
            text = pytesseract.image_to_string(image, lang=config.OCR_LANG)

            return text.strip()
        except Exception as e:
            logger.error(f"Ошибка OCR распознавания: {e}")
            return ""

    @staticmethod
    async def extract_code_from_screenshot(image_bytes: bytes) -> str:
        """Специализированное распознавание кода"""
        try:
            image = Image.open(io.BytesIO(image_bytes))

            # Настройки для лучшего распознавания кода
            custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789{}[]()<>;:=+-*/%&|!?.,"'

            text = pytesseract.image_to_string(
                image,
                lang='eng',
                config=custom_config
            )

            return text.strip()
        except Exception as e:
            logger.error(f"Ошибка распознавания кода: {e}")
            return ""


ocr_helper = OCRHelper()