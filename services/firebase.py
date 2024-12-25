import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from bot.config import logger

def initialize_firebase():
    """Инициализация Firebase"""
    try:
        # Путь к файлу с учетными данными Firebase
        cred_path = os.path.join('tests', 'botbtk-8ac0a-firebase-adminsdk-n5pjf-54392c0500.json')
        
        # Проверяем существование файла
        if not os.path.exists(cred_path):
            raise ValueError(f"Файл с учетными данными не найден: {cred_path}")

        try:
            # Инициализируем Firebase с учетными данными из файла
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            
            return firestore.client()

        except Exception as e:
            logger.error(f"Ошибка при инициализации Firebase: {e}")
            raise

    except Exception as e:
        logger.error(f"Ошибка при инициализации Firebase: {e}")
        raise

# Initialize Firebase and get database instance
db = initialize_firebase()