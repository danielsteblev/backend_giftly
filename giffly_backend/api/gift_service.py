import os
from django.conf import settings
from django.core.cache import cache
from .models import Product
from .serializers import ProductSerializer
import re

class GiftRecommendationService:
    def __init__(self):
        self.cache_timeout = 3600  # 1 час кэширования
        
        # Словарь синонимов для улучшения поиска
        self.synonyms = {
            'свадьба': ['свадебный', 'невеста', 'жених', 'свадебная', 'свадебное', 'свадебные'],
            'подарок': ['подарить', 'дарить', 'преподнести', 'презент', 'подарки'],
            'букет': ['букеты', 'цветы', 'цветочный', 'цветочная', 'цветочные'],
            'розы': ['роза', 'розовый', 'розовая', 'розовые'],
            'лилии': ['лилия', 'лилейный', 'лилейная'],
            'пионы': ['пион', 'пионовидный', 'пионовидная'],
            'гортензия': ['гортензии', 'гортензией'],
            'торжество': ['праздник', 'праздничный', 'праздничная', 'праздничные'],
            'юбилей': ['юбилейный', 'юбилейная', 'юбилейные'],
            'день рождения': ['день рождения', 'днюха', 'именины'],
        }
        
    def _get_cached_recommendations(self, query: str) -> dict:
        """Получает рекомендации из кэша"""
        cache_key = f"recommendations_{query.lower().strip()}"
        return cache.get(cache_key)
        
    def _cache_recommendations(self, query: str, recommendations: dict):
        """Сохраняет рекомендации в кэш"""
        cache_key = f"recommendations_{query.lower().strip()}"
        cache.set(cache_key, recommendations, self.cache_timeout)
        
    def _expand_keywords(self, keywords: list) -> list:
        """Расширяет список ключевых слов синонимами"""
        expanded_keywords = set(keywords)
        for keyword in keywords:
            # Ищем синонимы для каждого ключевого слова
            for main_word, synonyms in self.synonyms.items():
                if keyword in synonyms or keyword == main_word:
                    expanded_keywords.update(synonyms)
                    expanded_keywords.add(main_word)
        return list(expanded_keywords)
        
    def _extract_keywords(self, query: str) -> list:
        """Извлекает ключевые слова из запроса"""
        # Удаляем знаки препинания и приводим к нижнему регистру
        query = re.sub(r'[^\w\s]', '', query.lower())
        
        # Разбиваем на слова и удаляем стоп-слова
        stop_words = {'что', 'какой', 'какая', 'какие', 'как', 'для', 'на', 'в', 'и', 'или', 'а', 'но', 'по', 'с', 'от', 'к', 'у', 'о', 'об', 'за', 'под', 'над', 'перед', 'после', 'между', 'через', 'без', 'до', 'при', 'про', 'со', 'во', 'не', 'ни', 'же', 'бы', 'ли', 'быть', 'есть', 'был', 'была', 'были', 'было', 'подарить', 'подарок', 'дарить'}
        
        # Разбиваем на слова и обрабатываем составные слова
        words = []
        for word in query.split():
            if word not in stop_words and len(word) > 2:
                # Проверяем составные слова (например, "день рождения")
                if word == 'день' and 'рождения' in query.split():
                    words.append('день рождения')
                else:
                    words.append(word)
        
        # Расширяем ключевые слова синонимами
        return self._expand_keywords(words)
        
    def _find_matching_products(self, keywords: list) -> list:
        """Находит товары, соответствующие ключевым словам"""
        products = Product.objects.all()
        matching_products = []
        
        for product in products:
            # Проверяем совпадение в названии и описании
            product_text = f"{product.name.lower()} {product.description.lower()}"
            
            # Считаем совпадения с учетом синонимов
            matches = 0
            for keyword in keywords:
                if keyword in product_text:
                    matches += 1
                    # Дополнительные очки за совпадение в названии
                    if keyword in product.name.lower():
                        matches += 0.5
            
            if matches > 0:
                # Нормализуем score с учетом количества ключевых слов
                score = matches / (len(keywords) * 1.5)  # Уменьшаем вес количества ключевых слов
                matching_products.append({
                    'product': product,
                    'match_score': score
                })
        
        # Сортируем по score и берем топ-5
        matching_products.sort(key=lambda x: x['match_score'], reverse=True)
        return matching_products[:5]
        
    def get_recommendations(self, query: str) -> dict:
        """
        Получает рекомендации подарков на основе запроса пользователя
        
        Args:
            query (str): Запрос пользователя (например, "Зарекомендуй букет на свадьбу")
            
        Returns:
            dict: Словарь с результатами запроса
        """
        try:
            # Проверяем кэш
            cached_result = self._get_cached_recommendations(query)
            if cached_result:
                return cached_result

            # Извлекаем ключевые слова
            keywords = self._extract_keywords(query)
            if not keywords:
                return {
                    'success': False,
                    'error': 'Не удалось определить ключевые слова в запросе'
                }

            # Ищем подходящие товары
            matching_products = self._find_matching_products(keywords)
            
            if not matching_products:
                return {
                    'success': True,
                    'query': query,
                    'message': 'К сожалению, не удалось найти подходящие букеты по вашему запросу. Попробуйте изменить формулировку.',
                    'products': []
                }

            # Формируем ответ
            products_data = []
            for match in matching_products:
                product = match['product']
                serializer = ProductSerializer(product)
                products_data.append({
                    'product': serializer.data,
                    'relevance': round(match['match_score'] * 100)  # Процент релевантности
                })

            result = {
                'success': True,
                'query': query,
                'message': 'Вот подходящие букеты по вашему запросу:',
                'products': products_data
            }

            # Кэшируем результат
            self._cache_recommendations(query, result)
            
            return result

        except Exception as e:
            return {
                'success': False,
                'error': f'Произошла ошибка: {str(e)}'
            } 