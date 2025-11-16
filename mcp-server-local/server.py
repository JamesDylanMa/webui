"""
로컬 MCP 서버 예제
이 서버는 Open WebUI의 Agentic RAG와 통합할 수 있는 간단한 MCP 서버입니다.
HTTP 기반으로 동작하며, MCP SDK 없이도 실행 가능합니다.
"""

import json
import logging
import os
import requests
from typing import Any, Optional
from datetime import datetime
import pytz

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(title="Local MCP Server")

# CORS 설정 (Open WebUI에서 접근 가능하도록)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_tools_list():
    """도구 목록 반환"""
    return [
        {
            "name": "get_current_time",
            "description": "현재 시간과 날짜를 반환합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "시간대 (예: 'Asia/Seoul', 'UTC')",
                        "default": "Asia/Seoul"
                    }
                }
            }
        },
        {
            "name": "search_local_documents",
            "description": "로컬 문서를 검색합니다. 키워드나 질문을 입력하면 관련 문서를 찾아줍니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "검색할 키워드나 질문"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "최대 결과 수",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "calculate",
            "description": "수학 계산을 수행합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "계산할 수학 표현식 (예: '2 + 2', 'sqrt(16)')"
                    }
                },
                "required": ["expression"]
            }
        },
        {
            "name": "get_system_info",
            "description": "시스템 정보를 반환합니다.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "text_analysis",
            "description": "텍스트를 분석합니다 (단어 수, 문자 수, 감정 분석 등).",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "분석할 텍스트"
                    },
                    "analysis_type": {
                        "type": "string",
                        "description": "분석 유형: 'word_count', "char_count', 'sentiment'",
                        "default": "word_count"
                    }
                },
                "required": ["text"]
            }
        },
        {
            "name": "get_weather",
            "description": "특정 도시의 현재 날씨 정보를 조회합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "도시 이름 (예: 'Seoul', 'New York', 'Tokyo')"
                    },
                    "country_code": {
                        "type": "string",
                        "description": "국가 코드 (선택사항, 예: 'KR', 'US')",
                        "default": ""
                    }
                },
                "required": ["city"]
            }
        },
        {
            "name": "get_exchange_rate",
            "description": "환율 정보를 조회합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "from_currency": {
                        "type": "string",
                        "description": "기준 통화 코드 (예: 'USD', 'KRW', 'EUR')",
                        "default": "USD"
                    },
                    "to_currency": {
                        "type": "string",
                        "description": "대상 통화 코드 (예: 'KRW', 'USD', 'JPY')",
                        "default": "KRW"
                    }
                }
            }
        },
        {
            "name": "search_news",
            "description": "뉴스를 검색합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "검색할 키워드"
                    },
                    "language": {
                        "type": "string",
                        "description": "언어 코드 (예: 'ko', 'en')",
                        "default": "ko"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "최대 결과 수",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "get_stock_price",
            "description": "주식 가격 정보를 조회합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "주식 심볼 (예: 'AAPL', '005930' (삼성전자), 'TSLA')"
                    }
                },
                "required": ["symbol"]
            }
        },
        {
            "name": "get_crypto_price",
            "description": "암호화폐 가격 정보를 조회합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "암호화폐 심볼 (예: 'BTC', 'ETH', 'XRP')"
                    }
                },
                "required": ["symbol"]
            }
        },
        {
            "name": "translate_text",
            "description": "텍스트를 번역합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "번역할 텍스트"
                    },
                    "target_language": {
                        "type": "string",
                        "description": "대상 언어 코드 (예: 'ko', 'en', 'ja', 'zh')",
                        "default": "en"
                    },
                    "source_language": {
                        "type": "string",
                        "description": "원본 언어 코드 (자동 감지하려면 'auto')",
                        "default": "auto"
                    }
                },
                "required": ["text"]
            }
        },
        {
            "name": "search_wikipedia",
            "description": "위키피디아에서 정보를 검색합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "검색할 키워드"
                    },
                    "language": {
                        "type": "string",
                        "description": "언어 코드 (예: 'ko', 'en')",
                        "default": "ko"
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "get_quote",
            "description": "명언이나 격언을 반환합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "카테고리 (예: 'inspirational', 'motivational', 'success')",
                        "default": "inspirational"
                    }
                }
            }
        },
        {
            "name": "get_joke",
            "description": "유머러스한 농담이나 재미있는 이야기를 반환합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "카테고리 (예: 'general', 'programming', 'dad')",
                        "default": "general"
                    }
                }
            }
        },
        {
            "name": "get_random_fact",
            "description": "흥미로운 랜덤 사실을 반환합니다.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "ip_lookup",
            "description": "IP 주소의 위치 정보를 조회합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ip": {
                        "type": "string",
                        "description": "IP 주소 (비워두면 현재 IP 사용)",
                        "default": ""
                    }
                }
            }
        },
        {
            "name": "unit_converter",
            "description": "단위를 변환합니다 (길이, 무게, 온도 등).",
            "parameters": {
                "type": "object",
                "properties": {
                    "value": {
                        "type": "number",
                        "description": "변환할 값"
                    },
                    "from_unit": {
                        "type": "string",
                        "description": "원본 단위 (예: 'km', 'kg', 'celsius')"
                    },
                    "to_unit": {
                        "type": "string",
                        "description": "대상 단위 (예: 'mile', 'lb', 'fahrenheit')"
                    }
                },
                "required": ["value", "from_unit", "to_unit"]
            }
        }
    ]


async def execute_tool(name: str, arguments: dict) -> dict:
    """도구 실행 로직"""
    logger.info(f"Tool called: {name} with arguments: {arguments}")
    
    try:
        if name == "get_current_time":
            timezone_str = arguments.get("timezone", "Asia/Seoul")
            try:
                tz = pytz.timezone(timezone_str)
                current_time = datetime.now(tz)
            except:
                # 시간대가 유효하지 않으면 로컬 시간 사용
                current_time = datetime.now()
                timezone_str = "Local"
            
            # 한국어 요일 매핑
            weekdays_ko = {
                "Monday": "월요일",
                "Tuesday": "화요일",
                "Wednesday": "수요일",
                "Thursday": "목요일",
                "Friday": "금요일",
                "Saturday": "토요일",
                "Sunday": "일요일"
            }
            day_of_week_en = current_time.strftime("%A")
            day_of_week_ko = weekdays_ko.get(day_of_week_en, day_of_week_en)
            
            result = {
                "current_time": current_time.strftime("%Y-%m-%d %H:%M:%S"),
                "date": current_time.strftime("%Y년 %m월 %d일"),
                "time": current_time.strftime("%H시 %M분 %S초"),
                "day_of_week": day_of_week_ko,
                "day_of_week_en": day_of_week_en,
                "timezone": timezone_str,
                "timestamp": current_time.timestamp(),
                "formatted": f"{current_time.strftime('%Y년 %m월 %d일')} {day_of_week_ko} {current_time.strftime('%H시 %M분')} ({timezone_str})",
                "message": f"현재 시간은 {current_time.strftime('%Y년 %m월 %d일')} {day_of_week_ko} {current_time.strftime('%H시 %M분 %S초')}입니다."
            }
            return result
        
        elif name == "search_local_documents":
            query = arguments.get("query", "")
            max_results = arguments.get("max_results", 5)
            
            # 실제로는 벡터 DB나 파일 시스템을 검색하지만, 여기서는 예제 결과 반환
            results = [
                {
                    "title": f"문서 {i+1}: {query} 관련 내용",
                    "content": f"이 문서는 '{query}'에 대한 정보를 포함하고 있습니다. 실제 구현에서는 벡터 DB나 파일 시스템에서 검색합니다.",
                    "relevance_score": 0.9 - (i * 0.1)
                }
                for i in range(min(max_results, 5))
            ]
            
            return {
                "query": query,
                "results": results,
                "total_found": len(results)
            }
        
        elif name == "calculate":
            expression = arguments.get("expression", "")
            
            # 안전한 계산만 허용
            allowed_names = {
                "abs": abs, "round": round, "min": min, "max": max,
                "sum": sum, "pow": pow, "sqrt": lambda x: x ** 0.5
            }
            
            try:
                # 위험한 함수 제거
                result = eval(expression, {"__builtins__": {}}, allowed_names)
                return {
                    "expression": expression,
                    "result": result
                }
            except Exception as e:
                return {
                    "error": f"계산 오류: {str(e)}",
                    "expression": expression
                }
        
        elif name == "get_system_info":
            import platform
            import os
            
            info = {
                "platform": platform.system(),
                "platform_version": platform.version(),
                "python_version": platform.python_version(),
                "processor": platform.processor(),
                "hostname": platform.node(),
                "current_directory": os.getcwd()
            }
            
            return info
        
        elif name == "text_analysis":
            text = arguments.get("text", "")
            analysis_type = arguments.get("analysis_type", "word_count")
            
            if analysis_type == "word_count":
                word_count = len(text.split())
                char_count = len(text)
                char_count_no_spaces = len(text.replace(" ", ""))
                
                result = {
                    "text": text,
                    "word_count": word_count,
                    "character_count": char_count,
                    "character_count_no_spaces": char_count_no_spaces
                }
            elif analysis_type == "char_count":
                result = {
                    "text": text,
                    "character_count": len(text),
                    "character_count_no_spaces": len(text.replace(" ", "")),
                    "line_count": len(text.splitlines())
                }
            elif analysis_type == "sentiment":
                # 간단한 감정 분석 (실제로는 더 정교한 모델 사용)
                positive_words = ["좋", "좋아", "행복", "기쁘", "만족", "훌륭"]
                negative_words = ["나쁘", "슬프", "화나", "불만", "실망"]
                
                text_lower = text.lower()
                positive_score = sum(1 for word in positive_words if word in text_lower)
                negative_score = sum(1 for word in negative_words if word in text_lower)
                
                if positive_score > negative_score:
                    sentiment = "positive"
                elif negative_score > positive_score:
                    sentiment = "negative"
                else:
                    sentiment = "neutral"
                
                result = {
                    "text": text,
                    "sentiment": sentiment,
                    "positive_score": positive_score,
                    "negative_score": negative_score
                }
            else:
                result = {"error": f"알 수 없는 분석 유형: {analysis_type}"}
            
            return result
        
        elif name == "get_weather":
            city = arguments.get("city", "")
            country_code = arguments.get("country_code", "")
            
            # OpenWeatherMap API 사용 (무료 API 키 필요)
            # API 키가 없으면 예제 데이터 반환
            api_key = os.getenv("OPENWEATHER_API_KEY", "")
            
            if api_key:
                try:
                    url = f"http://api.openweathermap.org/data/2.5/weather"
                    params = {
                        "q": f"{city},{country_code}" if country_code else city,
                        "appid": api_key,
                        "units": "metric",
                        "lang": "kr"
                    }
                    response = requests.get(url, params=params, timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        return {
                            "city": data["name"],
                            "country": data["sys"]["country"],
                            "temperature": f"{data['main']['temp']}°C",
                            "feels_like": f"{data['main']['feels_like']}°C",
                            "description": data["weather"][0]["description"],
                            "humidity": f"{data['main']['humidity']}%",
                            "wind_speed": f"{data['wind']['speed']} m/s",
                            "pressure": f"{data['main']['pressure']} hPa"
                        }
                except Exception as e:
                    logger.warning(f"Weather API error: {e}")
            
            # API 키가 없거나 오류 발생 시 예제 데이터
            return {
                "city": city,
                "country": country_code or "Unknown",
                "temperature": "22°C",
                "feels_like": "21°C",
                "description": "맑음",
                "humidity": "65%",
                "wind_speed": "3.5 m/s",
                "pressure": "1013 hPa",
                "note": "OpenWeatherMap API 키를 설정하면 실제 날씨 정보를 받을 수 있습니다."
            }
        
        elif name == "get_exchange_rate":
            from_currency = arguments.get("from_currency", "USD").upper()
            to_currency = arguments.get("to_currency", "KRW").upper()
            
            # ExchangeRate-API 사용 (무료)
            try:
                url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    rate = data["rates"].get(to_currency)
                    if rate:
                        return {
                            "from_currency": from_currency,
                            "to_currency": to_currency,
                            "exchange_rate": rate,
                            "formatted": f"1 {from_currency} = {rate} {to_currency}",
                            "date": data.get("date", "")
                        }
            except Exception as e:
                logger.warning(f"Exchange rate API error: {e}")
            
            # 기본 환율 (예제)
            default_rates = {
                "USD": {"KRW": 1300, "EUR": 0.92, "JPY": 150},
                "KRW": {"USD": 0.00077, "EUR": 0.00071, "JPY": 0.12},
                "EUR": {"USD": 1.09, "KRW": 1413, "JPY": 163}
            }
            
            rate = default_rates.get(from_currency, {}).get(to_currency, 1.0)
            return {
                "from_currency": from_currency,
                "to_currency": to_currency,
                "exchange_rate": rate,
                "formatted": f"1 {from_currency} = {rate} {to_currency}",
                "note": "실시간 환율은 API 연결이 필요합니다."
            }
        
        elif name == "search_news":
            query = arguments.get("query", "")
            language = arguments.get("language", "ko")
            max_results = arguments.get("max_results", 5)
            
            # NewsAPI 사용 (API 키 필요)
            api_key = os.getenv("NEWS_API_KEY", "")
            
            if api_key:
                try:
                    url = "https://newsapi.org/v2/everything"
                    params = {
                        "q": query,
                        "language": language,
                        "sortBy": "publishedAt",
                        "pageSize": max_results,
                        "apiKey": api_key
                    }
                    response = requests.get(url, params=params, timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        articles = data.get("articles", [])
                        return {
                            "query": query,
                            "total_results": data.get("totalResults", 0),
                            "articles": [
                                {
                                    "title": article["title"],
                                    "description": article["description"],
                                    "url": article["url"],
                                    "published_at": article["publishedAt"]
                                }
                                for article in articles[:max_results]
                            ]
                        }
                except Exception as e:
                    logger.warning(f"News API error: {e}")
            
            # 예제 뉴스
            return {
                "query": query,
                "total_results": max_results,
                "articles": [
                    {
                        "title": f"{query} 관련 뉴스 {i+1}",
                        "description": f"{query}에 대한 최신 정보입니다.",
                        "url": f"https://example.com/news/{i+1}",
                        "published_at": datetime.now().isoformat()
                    }
                    for i in range(max_results)
                ],
                "note": "NewsAPI 키를 설정하면 실제 뉴스를 받을 수 있습니다."
            }
        
        elif name == "get_stock_price":
            symbol = arguments.get("symbol", "").upper()
            
            # Yahoo Finance 스크래핑 (간단한 예제)
            try:
                # 실제로는 yfinance 라이브러리 사용 권장
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    result = data.get("chart", {}).get("result", [])
                    if result:
                        meta = result[0].get("meta", {})
                        return {
                            "symbol": symbol,
                            "price": meta.get("regularMarketPrice", "N/A"),
                            "change": meta.get("regularMarketChange", "N/A"),
                            "change_percent": meta.get("regularMarketChangePercent", "N/A"),
                            "currency": meta.get("currency", "USD"),
                            "market_time": meta.get("regularMarketTime", "")
                        }
            except Exception as e:
                logger.warning(f"Stock API error: {e}")
            
            # 예제 데이터
            return {
                "symbol": symbol,
                "price": "150.25",
                "change": "+2.50",
                "change_percent": "+1.69%",
                "currency": "USD",
                "note": "실시간 주가 정보는 API 연결이 필요합니다."
            }
        
        elif name == "get_crypto_price":
            symbol = arguments.get("symbol", "").upper()
            
            # CoinGecko API 사용 (무료)
            try:
                url = f"https://api.coingecko.com/api/v3/simple/price"
                params = {
                    "ids": symbol.lower(),
                    "vs_currencies": "usd",
                    "include_24hr_change": "true"
                }
                response = requests.get(url, params=params, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    coin_data = data.get(symbol.lower(), {})
                    if coin_data:
                        return {
                            "symbol": symbol,
                            "price_usd": coin_data.get("usd", "N/A"),
                            "change_24h": coin_data.get("usd_24h_change", "N/A"),
                            "formatted": f"{symbol}: ${coin_data.get('usd', 'N/A')}"
                        }
            except Exception as e:
                logger.warning(f"Crypto API error: {e}")
            
            # 예제 데이터
            default_prices = {
                "BTC": 45000,
                "ETH": 2500,
                "XRP": 0.6
            }
            price = default_prices.get(symbol, 100)
            return {
                "symbol": symbol,
                "price_usd": price,
                "change_24h": "+2.5%",
                "formatted": f"{symbol}: ${price}",
                "note": "실시간 가격은 API 연결이 필요합니다."
            }
        
        elif name == "translate_text":
            text = arguments.get("text", "")
            target_lang = arguments.get("target_language", "en")
            source_lang = arguments.get("source_language", "auto")
            
            # MyMemory Translation API 사용 (무료, 제한 있음)
            try:
                url = "https://api.mymemory.translated.net/get"
                params = {
                    "q": text,
                    "langpair": f"{source_lang}|{target_lang}"
                }
                response = requests.get(url, params=params, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    translated = data.get("responseData", {}).get("translatedText", "")
                    return {
                        "original_text": text,
                        "translated_text": translated,
                        "source_language": source_lang,
                        "target_language": target_lang
                    }
            except Exception as e:
                logger.warning(f"Translation API error: {e}")
            
            # 간단한 예제 번역
            return {
                "original_text": text,
                "translated_text": f"[번역됨] {text}",
                "source_language": source_lang,
                "target_language": target_lang,
                "note": "실제 번역은 API 연결이 필요합니다."
            }
        
        elif name == "search_wikipedia":
            query = arguments.get("query", "")
            language = arguments.get("language", "ko")
            
            try:
                url = f"https://{language}.wikipedia.org/api/rest_v1/page/summary/{query}"
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "title": data.get("title", ""),
                        "extract": data.get("extract", ""),
                        "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                        "thumbnail": data.get("thumbnail", {}).get("source", "") if data.get("thumbnail") else ""
                    }
            except Exception as e:
                logger.warning(f"Wikipedia API error: {e}")
            
            return {
                "title": query,
                "extract": f"{query}에 대한 정보입니다.",
                "url": f"https://{language}.wikipedia.org/wiki/{query}",
                "note": "위키피디아에서 정보를 가져오는 중 오류가 발생했습니다."
            }
        
        elif name == "get_quote":
            category = arguments.get("category", "inspirational")
            
            quotes = {
                "inspirational": [
                    "성공은 준비된 자에게 찾아옵니다.",
                    "오늘 할 수 있는 일을 내일로 미루지 마세요.",
                    "실패는 성공의 어머니입니다."
                ],
                "motivational": [
                    "포기하지 않으면 반드시 성공합니다.",
                    "작은 시작이 큰 변화를 만듭니다.",
                    "꿈을 향해 한 걸음씩 나아가세요."
                ],
                "success": [
                    "성공은 목표를 향한 여정입니다.",
                    "노력하는 자에게 기회는 찾아옵니다.",
                    "성공은 준비와 기회가 만나는 곳입니다."
                ]
            }
            
            import random
            quote_list = quotes.get(category, quotes["inspirational"])
            quote = random.choice(quote_list)
            
            return {
                "quote": quote,
                "category": category
            }
        
        elif name == "get_joke":
            category = arguments.get("category", "general")
            
            jokes = {
                "general": [
                    "왜 컴퓨터가 추워요? 창문을 닫아서요!",
                    "프로그래머가 거울을 보면 뭐라고 하죠? Hello, World!",
                    "왜 수학책이 슬펐을까요? 문제가 너무 많아서요!"
                ],
                "programming": [
                    "왜 프로그래머는 다크 모드를 좋아할까요? 버그가 덜 보여서요!",
                    "프로그래머의 가장 큰 적은? 오타!",
                    "왜 함수가 화났을까요? 매개변수가 없어서요!"
                ],
                "dad": [
                    "아빠, 배고파요! 안녕 배고파, 나는 아빠야!",
                    "왜 책이 무서워했을까요? 페이지가 많아서요!",
                    "왜 시계가 3시를 좋아할까요? 시간이 되니까요!"
                ]
            }
            
            import random
            joke_list = jokes.get(category, jokes["general"])
            joke = random.choice(joke_list)
            
            return {
                "joke": joke,
                "category": category
            }
        
        elif name == "get_random_fact":
            facts = [
                "벌은 꿀을 만들기 위해 약 2백만 개의 꽃을 방문해야 합니다.",
                "지구의 대기는 약 78%가 질소로 구성되어 있습니다.",
                "인간의 뇌는 하루에 약 20와트의 전력을 사용합니다.",
                "바나나는 사실 베리(berry)가 아니라 베리입니다!",
                "해파리는 95%가 물로 구성되어 있습니다.",
                "코끼리는 땅을 통한 진동으로 소통할 수 있습니다.",
                "고양이는 약 200개의 서로 다른 소리를 낼 수 있습니다.",
                "지구상의 모든 개미의 무게는 모든 인간의 무게보다 큽니다."
            ]
            
            import random
            return {
                "fact": random.choice(facts)
            }
        
        elif name == "ip_lookup":
            ip = arguments.get("ip", "")
            
            if not ip:
                # 현재 IP 조회
                try:
                    response = requests.get("https://api.ipify.org?format=json", timeout=5)
                    if response.status_code == 200:
                        ip = response.json().get("ip", "")
                except:
                    pass
            
            if ip:
                try:
                    url = f"http://ip-api.com/json/{ip}"
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        return {
                            "ip": ip,
                            "country": data.get("country", ""),
                            "region": data.get("regionName", ""),
                            "city": data.get("city", ""),
                            "isp": data.get("isp", ""),
                            "lat": data.get("lat", ""),
                            "lon": data.get("lon", "")
                        }
                except Exception as e:
                    logger.warning(f"IP lookup error: {e}")
            
            return {
                "ip": ip or "Unknown",
                "note": "IP 위치 정보를 가져오는 중 오류가 발생했습니다."
            }
        
        elif name == "unit_converter":
            value = float(arguments.get("value", 0))
            from_unit = arguments.get("from_unit", "").lower()
            to_unit = arguments.get("to_unit", "").lower()
            
            # 단위 변환 테이블
            conversions = {
                # 길이
                "km": {"mile": 0.621371, "m": 1000, "cm": 100000},
                "mile": {"km": 1.60934, "m": 1609.34},
                "m": {"km": 0.001, "cm": 100, "mile": 0.000621371},
                "cm": {"m": 0.01, "km": 0.00001},
                # 무게
                "kg": {"lb": 2.20462, "g": 1000},
                "lb": {"kg": 0.453592, "g": 453.592},
                "g": {"kg": 0.001, "lb": 0.00220462},
                # 온도
                "celsius": {"fahrenheit": lambda x: x * 9/5 + 32, "kelvin": lambda x: x + 273.15},
                "fahrenheit": {"celsius": lambda x: (x - 32) * 5/9, "kelvin": lambda x: (x - 32) * 5/9 + 273.15},
                "kelvin": {"celsius": lambda x: x - 273.15, "fahrenheit": lambda x: (x - 273.15) * 9/5 + 32}
            }
            
            if from_unit in conversions and to_unit in conversions[from_unit]:
                converter = conversions[from_unit][to_unit]
                if callable(converter):
                    result = converter(value)
                else:
                    result = value * converter
                
                return {
                    "value": value,
                    "from_unit": from_unit,
                    "to_unit": to_unit,
                    "result": result,
                    "formatted": f"{value} {from_unit} = {result} {to_unit}"
                }
            else:
                return {
                    "error": f"{from_unit}에서 {to_unit}로의 변환이 지원되지 않습니다.",
                    "supported_units": list(conversions.keys())
                }
        
        else:
            return {"error": f"알 수 없는 도구: {name}"}
    
    except Exception as e:
        logger.exception(f"Error executing tool {name}: {e}")
        return {"error": f"도구 실행 오류: {str(e)}"}


# HTTP 엔드포인트
@app.get("/health")
async def health():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy", "server": "local-mcp-server"}


@app.get("/tools")
async def list_tools_http():
    """HTTP를 통한 도구 목록 조회"""
    tools_list = get_tools_list()
    return {
        "tools": tools_list
    }


@app.post("/tools/call")
async def call_tool_http(request: Request):
    """HTTP를 통한 도구 호출"""
    try:
        data = await request.json()
        tool_name = data.get("name")
        arguments = data.get("arguments", {})
        
        if not tool_name:
            raise HTTPException(status_code=400, detail="Tool name is required")
        
        # 도구 실행
        result = await execute_tool(tool_name, arguments)
        
        return {
            "success": True,
            "result": result
        }
    except Exception as e:
        logger.exception(f"Error calling tool via HTTP: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# MCP streamable HTTP 엔드포인트 (간단한 구현)
@app.post("/mcp/stream")
async def mcp_stream(request: Request):
    """MCP streamable HTTP 엔드포인트"""
    try:
        # MCP 프로토콜에 맞는 요청 처리
        # 실제 구현은 MCP SDK를 사용하거나 프로토콜 사양에 맞게 구현해야 함
        data = await request.json()
        
        if data.get("method") == "tools/list":
            tools_list = get_tools_list()
            return {
                "tools": [
                    {
                        "name": tool["name"],
                        "description": tool["description"],
                        "inputSchema": tool["parameters"]
                    }
                    for tool in tools_list
                ]
            }
        elif data.get("method") == "tools/call":
            tool_name = data.get("params", {}).get("name")
            arguments = data.get("params", {}).get("arguments", {})
            
            result = await execute_tool(tool_name, arguments)
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, ensure_ascii=False, indent=2)
                    }
                ]
            }
        else:
            return {"error": f"Unknown method: {data.get('method')}"}
    
    except Exception as e:
        logger.exception(f"Error in MCP stream: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


def run_http_server(host: str = "127.0.0.1", port: int = 8001):
    """HTTP 서버 실행"""
    logger.info(f"Starting MCP HTTP server on http://{host}:{port}")
    logger.info(f"Health check: http://{host}:{port}/health")
    logger.info(f"Tools list: http://{host}:{port}/tools")
    logger.info(f"MCP stream: http://{host}:{port}/mcp/stream")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_http_server()
