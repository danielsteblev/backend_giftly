import os
from django.conf import settings
from django.core.cache import cache
from .models import Product
from .serializers import ProductSerializer
import re
import logging

logger = logging.getLogger(__name__)

class GiftRecommendationService:
    def __init__(self):
        self.cache_timeout = 3600  # 1 час кэширования
        
        # Расширенный словарь синонимов для свадебной тематики
        self.synonyms = {
            'свадьба': [
                'свадебный', 'невеста', 'жених', 'свадебная', 'свадебное', 'свадебные',
                'свадьбы', 'свадебный букет', 'свадебная композиция', 'свадебная флористика',
                'свадебный декор', 'свадебное оформление', 'свадебная церемония'
            ],
            'подарок': [
                'подарить', 'дарить', 'преподнести', 'презент', 'подарки',
                'что подарить', 'какой подарок', 'выбрать подарок', 'идея подарка'
            ],
            'букет': [
                'букеты', 'цветы', 'цветочный', 'цветочная', 'цветочные',
                'композиция', 'флористика', 'флористический', 'флористическая',
                'свадебный букет', 'свадебная композиция', 'свадебная флористика'
            ],
            'розы': [
                'роза', 'розовый', 'розовая', 'розовые', 'розы',
                'красные розы', 'белые розы', 'розовые розы', 'пионовидные розы'
            ],
            'пионы': [
                'пион', 'пионовидный', 'пионовидная', 'пионовидные',
                'пионовидные розы', 'пионы', 'пионовый', 'пионовая'
            ],
            'гортензия': [
                'гортензии', 'гортензией', 'гортензиевый', 'гортензиевая',
                'синяя гортензия', 'розовая гортензия', 'белая гортензия'
            ],
            'торжество': [
                'праздник', 'праздничный', 'праздничная', 'праздничные',
                'торжественный', 'торжественная', 'торжественные',
                'свадебное торжество', 'свадебный праздник'
            ],
            'невеста': [
                'невесты', 'невест', 'невесте', 'невестой',
                'свадебный букет невесты', 'букет для невесты',
                'свадебная композиция невесты'
            ],
            'жених': [
                'жениха', 'жениху', 'женихом',
                'бутоньерка', 'бутоньерки', 'бутоньерку',
                'свадебная бутоньерка', 'бутоньерка жениха'
            ],
            'свадебный букет': [
                'свадебная композиция', 'свадебная флористика',
                'букет невесты', 'букет для невесты',
                'свадебный букет невесты', 'свадебная композиция невесты'
            ]
        }
        
        # Важные фразы и их контексты
        self.protected_phrases = {
            'свадьба': [
                'на свадьбу', 'для свадьбы', 'на свадебное торжество',
                'для свадебной церемонии', 'на свадебное мероприятие'
            ],
            'подарок': [
                'что подарить', 'какой подарок', 'выбрать подарок',
                'идея подарка', 'подарить на', 'подарок для'
            ],
            'букет': [
                'свадебный букет', 'букет на свадьбу', 'букет для свадьбы',
                'букет невесты', 'букет для невесты'
            ]
        }
        
        # Минимальные стоп-слова, которые не влияют на поиск
        self.stop_words = {'что', 'какой', 'какая', 'какие', 'как', 'в', 'и', 'или', 'а', 'но'}
        
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
        
        # Добавляем все синонимы для каждого ключевого слова
        for keyword in keywords:
            for main_word, synonyms in self.synonyms.items():
                if keyword in synonyms or keyword == main_word:
                    expanded_keywords.update(synonyms)
                    expanded_keywords.add(main_word)
                    
                    # Добавляем составные фразы
                    if keyword in ['свадьба', 'свадебный']:
                        expanded_keywords.update(['свадебный букет', 'свадебная композиция'])
                    elif keyword in ['невеста', 'невесты']:
                        expanded_keywords.update(['букет невесты', 'свадебный букет невесты'])
                    elif keyword in ['жених', 'жениха']:
                        expanded_keywords.update(['бутоньерка жениха', 'свадебная бутоньерка'])
        
        return list(expanded_keywords)
        
    def _extract_keywords(self, query: str) -> list:
        """Извлекает ключевые слова из запроса"""
        # Удаляем знаки препинания и приводим к нижнему регистру
        query = re.sub(r'[^\w\s]', '', query.lower())
        
        # Разбиваем на слова
        words = query.split()
        
        # Собираем ключевые слова
        keywords = []
        
        # Ищем важные фразы
        for i in range(len(words)):
            # Проверяем двухсловные фразы
            if i + 1 < len(words):
                phrase = f"{words[i]} {words[i+1]}"
                for main_word, phrases in self.protected_phrases.items():
                    if phrase in phrases:
                        keywords.append(phrase)
                        keywords.append(main_word)
            
            # Добавляем отдельные слова, если они не стоп-слова
            if words[i] not in self.stop_words and len(words[i]) > 2:
                keywords.append(words[i])
        
        # Расширяем ключевые слова синонимами
        expanded_keywords = self._expand_keywords(keywords)
        
        logger.info(f"Original query: {query}")
        logger.info(f"Extracted keywords: {keywords}")
        logger.info(f"Expanded keywords: {expanded_keywords}")
        
        return expanded_keywords
        
    def _find_matching_products(self, keywords: list) -> list:
        """Находит товары, соответствующие ключевым словам"""
        products = Product.objects.all()
        matching_products = []
        
        for product in products:
            # Проверяем совпадение в названии и описании
            product_text = f"{product.name.lower()} {product.description.lower()}"
            
            # Считаем совпадения с учетом синонимов
            matches = 0
            max_possible_matches = len(keywords)
            
            for keyword in keywords:
                # Базовое совпадение
                if keyword in product_text:
                    matches += 1
                    
                    # Дополнительные очки за совпадение в названии
                    if keyword in product.name.lower():
                        matches += 0.5
                    
                    # Дополнительные очки за точное совпадение фразы
                    if len(keyword.split()) > 1 and keyword in product_text:
                        matches += 0.5
                    
                    # Дополнительные очки за свадебную тематику
                    if any(sw in keyword for sw in ['свадьба', 'свадебный', 'невеста', 'жених']):
                        matches += 0.5
            
            if matches > 0:
                # Нормализуем score с учетом количества ключевых слов
                # Используем более мягкую нормализацию
                score = matches / (max_possible_matches * 0.8)
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
            query (str): Запрос пользователя (например, "Что подарить на свадьбу?")
            
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
                    'message': 'К сожалению, не удалось найти подходящие букеты по вашему запросу. Попробуйте изменить формулировку или уточнить детали (например, "Свадебный букет для невесты" или "Букет из роз на свадьбу").',
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
            logger.exception("Error in get_recommendations")
            return {
                'success': False,
                'error': f'Произошла ошибка: {str(e)}'
            } 