import os
import requests
from django.conf import settings
from .models import Product
from .serializers import ProductSerializer

class GiftRecommendationService:
    def __init__(self):
        self.api_key = os.getenv('DEEPSEEK_API_KEY')
        self.api_url = "https://api.deepseek.com/chat/completions"  # Официальный URL DeepSeek API
        
    def get_recommendations(self, query: str) -> dict:
        """
        Получает рекомендации подарков на основе запроса пользователя
        
        Args:
            query (str): Запрос пользователя (например, "Что подарить на свадьбу?")
            
        Returns:
            dict: Словарь с результатами запроса
        """
        try:
            # Проверяем API ключ
            if not self.api_key:
                return {
                    'success': False,
                    'error': 'API ключ не настроен. Добавьте DEEPSEEK_API_KEY в .env файл'
                }

            # Получаем товары из базы данных
            products = Product.objects.all()
            products_data = ProductSerializer(products, many=True).data

            # Формируем промпт для API
            products_text = "\n".join([
                f"{i+1}. {p['name']} — {p['description']} (Цена: {p['price']} руб.)"
                for i, p in enumerate(products_data)
            ])

            prompt = f"""У меня есть список товаров с описаниями:

{products_text}

Вопрос: {query}

Пожалуйста, проанализируй список товаров и дай рекомендации по подарку. 
Учитывай описание товаров и контекст вопроса.
Ответ должен быть структурированным и содержать конкретные рекомендации из списка товаров.
Для каждого рекомендованного товара укажи его номер из списка."""

            # Отправляем запрос к API
            response = requests.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",  # Официальная модель DeepSeek
                    "messages": [
                        {"role": "system", "content": "You are a helpful gift recommendation assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 1000,
                    "stream": False
                },
                timeout=30
            )

            # Проверяем ответ
            response.raise_for_status()
            result = response.json()
            
            # Получаем рекомендации из ответа
            recommendations = result["choices"][0]["message"]["content"]
            
            return {
                'success': True,
                'query': query,
                'recommendations': recommendations,
                'products_count': len(products_data)
            }

        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Ошибка при обращении к API: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Произошла ошибка: {str(e)}'
            } 