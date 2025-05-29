import os
from django.conf import settings
from django.core.cache import cache
from .models import Product
from .serializers import ProductSerializer
import re
import logging
from gigachat import GigaChat
from typing import List, Dict, Any, Optional
import json
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class GigaChatService:
    def __init__(self):
        self.client = None
        self.token_cache_key = 'gigachat_token'
        self.token_expiry_cache_key = 'gigachat_token_expiry'
        self.token_refresh_interval = 3600  # 1 час в секундах
        self.max_retries = 3
        self.retry_delay = 2
        self._initialize_client()
        
    def _get_cached_token(self) -> Optional[str]:
        """Получает токен из кэша"""
        token = cache.get(self.token_cache_key)
        expiry = cache.get(self.token_expiry_cache_key)
        
        if token and expiry and datetime.fromisoformat(expiry) > datetime.now():
            return token
        return None
        
    def _cache_token(self, token: str):
        """Сохраняет токен в кэш с временем истечения"""
        expiry = datetime.now() + timedelta(seconds=self.token_refresh_interval)
        cache.set(self.token_cache_key, token, self.token_refresh_interval)
        cache.set(self.token_expiry_cache_key, expiry.isoformat(), self.token_refresh_interval)
        
    def _initialize_client(self):
        """Инициализация клиента GigaChat с автоматическим обновлением токена"""
        try:
            credentials = os.getenv('GIGACHAT_CREDENTIALS')
            if not credentials:
                logger.error("GIGACHAT_CREDENTIALS not found in environment variables")
                return
                
            # Пробуем получить токен из кэша
            token = self._get_cached_token()
            
            if token:
                logger.info("Using cached GigaChat token")
                self.client = GigaChat(credentials=token, verify_ssl_certs=False)
            else:
                logger.info("Initializing new GigaChat client with credentials")
                self.client = GigaChat(credentials=credentials, verify_ssl_certs=False)
                # Кэшируем новый токен
                if hasattr(self.client, '_access_token'):
                    self._cache_token(self.client._access_token)
                    
            logger.info("GigaChat client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize GigaChat client: {str(e)}")
            
    def _refresh_token(self):
        """Обновляет токен GigaChat"""
        try:
            credentials = os.getenv('GIGACHAT_CREDENTIALS')
            if not credentials:
                logger.error("GIGACHAT_CREDENTIALS not found in environment variables")
                return False
                
            logger.info("Refreshing GigaChat token")
            self.client = GigaChat(credentials=credentials, verify_ssl_certs=False)
            
            if hasattr(self.client, '_access_token'):
                self._cache_token(self.client._access_token)
                logger.info("GigaChat token refreshed successfully")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to refresh GigaChat token: {str(e)}")
            return False
            
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Анализирует запрос пользователя с помощью GigaChat с автоматическим обновлением токена
        
        Args:
            query (str): Запрос пользователя
            
        Returns:
            Dict[str, Any]: Результат анализа запроса
        """
        if not self.client:
            logger.error("GigaChat client not initialized")
            return {}
            
        for attempt in range(self.max_retries):
            try:
                prompt = f"""
                Проанализируй запрос пользователя и выдели следующие аспекты:
                1. Основная тема (свадьба, день рождения и т.д.)
                2. Тип букета (свадебный, праздничный и т.д.)
                3. Предпочтения по цветам
                4. Бюджет (если указан)
                5. Особые пожелания
                
                Запрос: {query}
                
                Ответ дай в формате JSON со следующими полями:
                {{
                    "theme": "основная тема",
                    "type": "тип букета",
                    "colors": ["предпочтительные цвета"],
                    "budget": "бюджет или null",
                    "special_requests": ["особые пожелания"],
                    "keywords": ["ключевые слова для поиска"]
                }}
                """
                
                response = self.client.chat(prompt)
                logger.info(f"Raw GigaChat response: {response}")
                
                if not response or not response.choices:
                    logger.error("Empty response from GigaChat")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        continue
                    return {}
                    
                content = response.choices[0].message.content
                logger.info(f"GigaChat content: {content}")
                
                # Очищаем ответ от возможных лишних символов
                content = content.strip()
                if content.startswith('```json'):
                    content = content[7:]
                if content.endswith('```'):
                    content = content[:-3]
                content = content.strip()
                
                try:
                    result = json.loads(content)
                    logger.info(f"Parsed GigaChat result: {result}")
                    return result
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse GigaChat response as JSON: {e}")
                    logger.error(f"Content that failed to parse: {content}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        continue
                    return {}
                
            except Exception as e:
                error_str = str(e)
                logger.error(f"Error in GigaChat analysis (attempt {attempt + 1}/{self.max_retries}): {error_str}")
                
                # Если токен истек или недействителен, пробуем обновить
                if "401" in error_str or "credentials" in error_str.lower():
                    if self._refresh_token():
                        continue
                
                # Если превышен лимит запросов, ждем подольше
                if "429" in error_str:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                    
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                return {}
        
        return {}

class GiftRecommendationService:
    def __init__(self):
        self.cache_timeout = 3600  # 1 час кэширования
        self.gigachat_service = GigaChatService()
        
        # Словарь цветов и их синонимов
        self.flower_types = {
            'розы': {
                'keywords': ['роза', 'розы', 'розовый', 'розовая', 'розовые'],
                'varieties': ['пионовидные', 'кустовые', 'маритим', 'барбадос', 'классические'],
                'weight': 2.0  # Базовый вес для роз
            },
            'лилии': {
                'keywords': ['лилия', 'лилии', 'лилейный', 'лилейная'],
                'varieties': ['белые', 'розовые', 'оранжевые', 'тигровые'],
                'weight': 1.8
            },
            'пионы': {
                'keywords': ['пион', 'пионы', 'пионовидный', 'пионовидная'],
                'varieties': ['розовые', 'белые', 'бордовые'],
                'weight': 1.8
            },
            'гортензии': {
                'keywords': ['гортензия', 'гортензии', 'гортензиевый'],
                'varieties': ['синие', 'розовые', 'белые', 'фиолетовые'],
                'weight': 1.5
            },
            'тюльпаны': {
                'keywords': ['тюльпан', 'тюльпаны', 'тюльпановый'],
                'varieties': ['красные', 'розовые', 'белые', 'желтые'],
                'weight': 1.5
            },
            'орхидеи': {
                'keywords': ['орхидея', 'орхидеи', 'орхидейный'],
                'varieties': ['фаленопсис', 'цимбидиум', 'дендробиум'],
                'weight': 1.7
            }
        }
        
        # Словарь цветовых сочетаний
        self.color_combinations = {
            'классический': ['красный', 'белый', 'зеленый'],
            'романтический': ['розовый', 'белый', 'пастельный'],
            'свадебный': ['белый', 'кремовый', 'нежно-розовый'],
            'яркий': ['красный', 'оранжевый', 'желтый'],
            'нежный': ['розовый', 'сиреневый', 'белый'],
            'осенний': ['оранжевый', 'бордовый', 'желтый']
        }
        
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
            
            # Добавляем синонимы для цветов
            for flower_type, data in self.flower_types.items():
                if keyword in data['keywords']:
                    expanded_keywords.update(data['keywords'])
                    expanded_keywords.add(flower_type)
        
        return list(expanded_keywords)
        
    def _calculate_flower_relevance(self, product_text: str, query_keywords: list) -> float:
        """Рассчитывает релевантность по типу цветов"""
        relevance = 0.0
        matched_flowers = set()
        
        # Проверяем каждый тип цветов
        for flower_type, data in self.flower_types.items():
            # Проверяем, есть ли этот тип цветов в запросе
            is_requested = any(keyword in data['keywords'] for keyword in query_keywords)
            
            if is_requested:
                # Проверяем наличие цветов в тексте продукта
                for keyword in data['keywords']:
                    if keyword in product_text:
                        # Базовые очки за совпадение типа цветов
                        relevance += data['weight']
                        matched_flowers.add(flower_type)
                        
                        # Дополнительные очки за сорта
                        for variety in data['varieties']:
                            if variety in product_text:
                                relevance += 0.3
                                
                        # Дополнительные очки за точное совпадение в названии
                        if any(keyword in product_text.split()[0:3] for keyword in data['keywords']):
                            relevance += 0.5
                            
                        break  # Прекращаем поиск после первого совпадения для этого типа
        
        # Бонус за соответствие цветовой гамме
        for style, colors in self.color_combinations.items():
            if any(color in query_keywords for color in colors):
                if any(color in product_text for color in colors):
                    relevance += 0.4
        
        return relevance
        
    def _extract_keywords(self, query: str) -> list:
        """Извлекает ключевые слова из запроса с помощью GigaChat и базового анализа"""
        # Получаем анализ от GigaChat
        ai_analysis = self.gigachat_service.analyze_query(query)
        logger.info(f"AI analysis in _extract_keywords: {ai_analysis}")
        
        # Базовый анализ запроса
        query = re.sub(r'[^\w\s]', '', query.lower())
        words = query.split()
        logger.info(f"Base words from query: {words}")
        
        # Объединяем результаты базового анализа и AI
        keywords = set()
        
        # Добавляем ключевые слова из AI анализа только если они явно указаны в запросе
        if ai_analysis:
            # Проверяем, есть ли свадебная тематика в исходном запросе
            has_wedding_context = any(word in query.lower() for word in ['свадьба', 'свадебный', 'невеста', 'жених'])
            
            if 'keywords' in ai_analysis and ai_analysis['keywords']:
                # Фильтруем свадебные ключевые слова, если их нет в запросе
                filtered_keywords = []
                for k in ai_analysis['keywords']:
                    if k is None:
                        continue
                    if not has_wedding_context and any(wedding_word in k.lower() for wedding_word in ['свадьба', 'свадебный', 'невеста', 'жених']):
                        continue
                    filtered_keywords.append(k)
                logger.info(f"Adding filtered keywords from AI: {filtered_keywords}")
                keywords.update(filtered_keywords)
            
            # Добавляем тип и тему только если они не свадебные или свадьба явно указана
            if 'type' in ai_analysis and ai_analysis['type']:
                if has_wedding_context or not any(wedding_word in ai_analysis['type'].lower() for wedding_word in ['свадьба', 'свадебный', 'невеста']):
                    logger.info(f"Adding type from AI: {ai_analysis['type']}")
                    keywords.add(ai_analysis['type'])
            
            if 'theme' in ai_analysis and ai_analysis['theme']:
                if has_wedding_context or not any(wedding_word in ai_analysis['theme'].lower() for wedding_word in ['свадьба', 'свадебный', 'невеста']):
                    logger.info(f"Adding theme from AI: {ai_analysis['theme']}")
                    keywords.add(ai_analysis['theme'])
            
            if 'colors' in ai_analysis and ai_analysis['colors']:
                logger.info(f"Adding colors from AI: {ai_analysis['colors']}")
                keywords.update(c for c in ai_analysis['colors'] if c is not None)
        
        # Добавляем результаты базового анализа
        for i in range(len(words)):
            if i + 1 < len(words):
                phrase = f"{words[i]} {words[i+1]}"
                for main_word, phrases in self.protected_phrases.items():
                    if phrase in phrases:
                        # Проверяем контекст для свадебных фраз
                        if 'свадьба' in main_word.lower() and not any(wedding_word in query.lower() for wedding_word in ['свадьба', 'свадебный', 'невеста', 'жених']):
                            continue
                        logger.info(f"Adding protected phrase: {phrase} -> {main_word}")
                        keywords.add(phrase)
                        keywords.add(main_word)
            
            if words[i] not in self.stop_words and len(words[i]) > 2:
                logger.info(f"Adding base word: {words[i]}")
                keywords.add(words[i])
        
        # Расширяем ключевые слова синонимами
        logger.info(f"Keywords before expansion: {list(keywords)}")
        expanded_keywords = self._expand_keywords(list(keywords))
        logger.info(f"Keywords after expansion: {expanded_keywords}")
        
        # Фильтруем None значения и пустые строки
        final_keywords = [k for k in expanded_keywords if k is not None and k.strip()]
        logger.info(f"Final keywords: {final_keywords}")
        
        return final_keywords
        
    def _extract_budget_from_query(self, query: str) -> Optional[int]:
        """Извлекает бюджет из текста запроса"""
        try:
            # Ищем числа после слов "до", "ценой", "стоимостью", "бюджет"
            budget_patterns = [
                r'до\s+(\d+)\s*(?:руб|₽|рублей|рубля)?',
                r'ценой\s+до\s+(\d+)\s*(?:руб|₽|рублей|рубля)?',
                r'стоимостью\s+до\s+(\d+)\s*(?:руб|₽|рублей|рубля)?',
                r'бюджет\s+(\d+)\s*(?:руб|₽|рублей|рубля)?',
                r'(\d+)\s*(?:руб|₽|рублей|рубля)\s+максимум',
                r'не\s+дороже\s+(\d+)\s*(?:руб|₽|рублей|рубля)?',
                # Новые паттерны
                r'с\s+бюджет\s+(\d+)\s*(?:руб|₽|рублей|рубля)?',
                r'бюджетом\s+(\d+)\s*(?:руб|₽|рублей|рубля)?',
                r'в\s+пределах\s+(\d+)\s*(?:руб|₽|рублей|рубля)?',
                r'примерно\s+(\d+)\s*(?:руб|₽|рублей|рубля)?',
                r'около\s+(\d+)\s*(?:руб|₽|рублей|рубля)?',
                r'за\s+(\d+)\s*(?:руб|₽|рублей|рубля)?',
                r'по\s+цене\s+(\d+)\s*(?:руб|₽|рублей|рубля)?',
                r'стоимость\s+(\d+)\s*(?:руб|₽|рублей|рубля)?'
            ]
            
            for pattern in budget_patterns:
                match = re.search(pattern, query.lower())
                if match:
                    budget = int(match.group(1))
                    logger.info(f"Extracted budget from query using pattern '{pattern}': {budget}")
                    return budget
                    
            # Если не нашли по паттернам, ищем просто число после слова "бюджет"
            budget_match = re.search(r'бюджет\s+(\d+)', query.lower())
            if budget_match:
                budget = int(budget_match.group(1))
                logger.info(f"Extracted budget using fallback pattern: {budget}")
                return budget
                
            return None
        except Exception as e:
            logger.error(f"Error extracting budget from query: {e}")
            return None

    def _find_matching_products(self, keywords: list) -> list:
        """Находит товары, соответствующие ключевым словам с учетом AI анализа и бюджета"""
        products = Product.objects.all()
        matching_products = []
        
        # Получаем AI анализ для контекста
        ai_analysis = self.gigachat_service.analyze_query(" ".join(keywords))
        
        # Извлекаем бюджет из AI анализа и напрямую из запроса
        budget = None
        if ai_analysis and 'budget' in ai_analysis:
            budget_value = ai_analysis['budget']
            if budget_value is not None:
                try:
                    budget_str = re.sub(r'[^\d]', '', str(budget_value))
                    if budget_str:
                        budget = int(budget_str)
                        logger.info(f"Extracted budget from AI analysis: {budget}")
                except (ValueError, TypeError) as e:
                    logger.error(f"Error parsing budget from AI: {e}")
        
        if budget is None:
            budget = self._extract_budget_from_query(" ".join(keywords))
            if budget and ai_analysis:
                ai_analysis['budget'] = str(budget)
                logger.info(f"Updated AI analysis with extracted budget: {budget}")
        
        # Фильтруем продукты по бюджету
        filtered_products = []
        for product in products:
            try:
                product_price = float(product.price)
                if budget is None or product_price <= budget:
                    filtered_products.append(product)
                    logger.info(f"Product {product.name} (price: {product_price}) within budget {budget}")
                else:
                    logger.info(f"Skipping product {product.name} - price {product_price} exceeds budget {budget}")
            except (ValueError, TypeError) as e:
                logger.error(f"Error comparing prices for product {product.name}: {e}")
                continue
        
        for product in filtered_products:
            product_text = f"{product.name.lower()} {product.description.lower()}"
            matches = 0
            max_possible_matches = len(keywords)
            
            # Проверяем наличие свадебного контекста в запросе
            has_wedding_context = any(word in ' '.join(keywords).lower() for word in ['свадьба', 'свадебный', 'невеста', 'жених'])
            
            # Рассчитываем релевантность по цветам
            flower_relevance = self._calculate_flower_relevance(product_text, keywords)
            
            # Базовые совпадения по ключевым словам
            for keyword in keywords:
                if keyword is None:
                    continue
                    
                if keyword in product_text:
                    matches += 1
                    
                    # Дополнительные очки за совпадение в названии
                    if keyword in product.name.lower():
                        matches += 0.5
                    
                    # Дополнительные очки за точное совпадение фразы
                    if len(keyword.split()) > 1 and keyword in product_text:
                        matches += 0.3
                    
                    # Дополнительные очки за свадебную тематику только если она явно указана
                    if has_wedding_context and any(sw in keyword for sw in ['свадьба', 'свадебный', 'невеста']):
                        matches += 0.3
                    elif not has_wedding_context and any(sw in keyword for sw in ['свадьба', 'свадебный', 'невеста']):
                        matches -= 0.2  # Штраф за свадебную тематику, если она не запрошена
                        
                    # Дополнительные очки за совпадение с AI анализом
                    if ai_analysis:
                        if 'type' in ai_analysis and ai_analysis['type'] and ai_analysis['type'] in product_text:
                            if has_wedding_context or 'свадьба' not in ai_analysis['type'].lower():
                                matches += 0.2
                        if 'theme' in ai_analysis and ai_analysis['theme'] and ai_analysis['theme'] in product_text:
                            if has_wedding_context or 'свадьба' not in ai_analysis['theme'].lower():
                                matches += 0.2
            
            if matches > 0 or flower_relevance > 0:
                # Базовый score с учетом релевантности цветов
                base_score = (matches + flower_relevance) / (max_possible_matches * 0.8)
                
                # Корректируем score с учетом бюджета
                if budget is not None:
                    try:
                        product_price = float(product.price)
                        # Если цена близка к бюджету (в пределах 20%), повышаем релевантность
                        if product_price >= budget * 0.8:
                            base_score *= 1.1
                    except (ValueError, TypeError) as e:
                        logger.error(f"Error adjusting score by budget: {e}")
                
                # Штраф за свадебную тематику, если она не запрошена
                if not has_wedding_context and any(word in product_text for word in ['свадьба', 'свадебный', 'невеста']):
                    base_score *= 0.7
                
                matching_products.append({
                    'product': product,
                    'match_score': base_score,
                    'ai_analysis': ai_analysis,
                    'budget_match': True if budget is not None else None,
                    'flower_relevance': flower_relevance
                })
        
        # Сортируем по убыванию релевантности
        matching_products.sort(key=lambda x: x['match_score'], reverse=True)
        return matching_products[:5]
        
    def get_recommendations(self, query: str) -> dict:
        """
        Получает рекомендации подарков на основе запроса пользователя с использованием AI
        
        Args:
            query (str): Запрос пользователя
            
        Returns:
            dict: Словарь с результатами запроса
        """
        try:
            cached_result = self._get_cached_recommendations(query)
            if cached_result:
                return cached_result

            keywords = self._extract_keywords(query)
            if not keywords:
                return {
                    'success': False,
                    'error': 'Не удалось определить ключевые слова в запросе'
                }

            matching_products = self._find_matching_products(keywords)
            
            if not matching_products:
                return {
                    'success': True,
                    'query': query,
                    'message': 'К сожалению, не удалось найти подходящие букеты по вашему запросу. Попробуйте изменить формулировку или уточнить детали.',
                    'products': []
                }

            products_data = []
            for match in matching_products:
                product = match['product']
                serializer = ProductSerializer(product)
                product_data = {
                    'product': serializer.data,
                    'relevance': round(match['match_score'] * 100)
                }
                
                # Добавляем AI анализ, если он есть
                if 'ai_analysis' in match:
                    product_data['ai_analysis'] = match['ai_analysis']
                
                # Добавляем информацию о соответствии бюджету
                if 'budget_match' in match and match['budget_match'] is not None:
                    product_data['budget_match'] = match['budget_match']
                    if hasattr(product, 'price') and 'ai_analysis' in match and 'budget' in match['ai_analysis']:
                        product_data['budget_info'] = {
                            'product_price': product.price,
                            'requested_budget': match['ai_analysis']['budget']
                        }
                
                products_data.append(product_data)

            # Формируем сообщение с учетом бюджета
            message = 'Вот подходящие букеты по вашему запросу:'
            if any('budget' in p.get('ai_analysis', {}) for p in products_data):
                budget_products = [p for p in products_data if p.get('budget_match', True)]
                if len(budget_products) < len(products_data):
                    message += ' (Некоторые букеты могут не соответствовать указанному бюджету)'

            result = {
                'success': True,
                'query': query,
                'message': message,
                'products': products_data
            }

            self._cache_recommendations(query, result)
            return result

        except Exception as e:
            logger.exception("Error in get_recommendations")
            return {
                'success': False,
                'error': f'Произошла ошибка: {str(e)}'
            } 