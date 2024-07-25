# импорты
import asyncio
import websockets
import json
import logging
import requests
from fastapi import FastAPI, Query
from typing import Optional

# логирования приложения
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# параметры конфигурации 
BINANCE_URI = "wss://stream.binance.com:9443/ws/!ticker@arr"
KRAKEN_URI = "wss://ws.kraken.com/"
CHUNK_SIZE = 100  # Размер чанка для подписки на пары (Из-за ограничений API)

# Словарь для нормализации пар
PAIR_NORMALIZATION = {
    'BTC': 'XBT',
    'USDT': 'USD',
    'TUSD': 'USD',
    'DAI': 'USD',
    'BUSD': 'USD',
    'USDC': 'USD',
    'WBTC': 'XBT'
}

def normalize_pair_name(pair: str) -> str:
    """Нормализуем имена пар по словарю PAIR_NORMALIZATION."""
    for key, value in PAIR_NORMALIZATION.items():
        pair = pair.replace(key, value)
    
    return pair

def transform_pair_format(pair: str) -> str:
    """Преобразуем пары из формата 'BTCUSD' в формат 'BTC/USD'."""
    if '/' in pair:
        base, quote = pair.split('/')
    else:
        base, quote = pair[:3], pair[3:]
    
    return f"{base}/{quote}"

class BinanceClient:
    def __init__(self):
        self.uri = BINANCE_URI
        # Цены пар
        self.prices = {}

    async def connect(self):
        """Устанавливает соединение с WebSocket и обрабатываем ивент сообщения."""
        async with websockets.connect(self.uri) as websocket:
            async for message in websocket:
                data = json.loads(message)
                self.handle_message(data)

    def handle_message(self, data):
        """Обрабатываем полученные данные и обновляем цены по парам."""
        for ticker in data:
            pair = self.normalize_pair(ticker['s'])
            avg_price = (float(ticker['b']) + float(ticker['a'])) / 2
            self.prices[pair] = avg_price
            logger.info(f"Binance updated {pair}: {avg_price}")

    def normalize_pair(self, pair):
        """Нормализуем имя пары."""
        return normalize_pair_name(transform_pair_format(pair.replace('_', '/').upper()))

class KrakenClient:
    def __init__(self):
        self.uri = KRAKEN_URI
        # Цены
        self.prices = {}
        # Возможные пары
        self.pairs = self.get_trading_pairs()
        logger.info(f"Kraken pairs: {self.pairs}")

    def get_trading_pairs(self):
        """Получаем доступные пары с биржи Kraken для создания подписки."""
        response = requests.get("https://api.kraken.com/0/public/AssetPairs")
        data = response.json()
        pairs = [details['wsname'] for _, details in data['result'].items()]
        return pairs

    async def connect(self):
        """Устанавливает соединение с WebSocket и подписывается на пары."""
        pairs_chunk = [self.subscribe_to_pairs(self.pairs[i:i + CHUNK_SIZE]) for i in range(0, len(self.pairs), CHUNK_SIZE)]
        await asyncio.gather(*pairs_chunk)

    async def subscribe_to_pairs(self, pairs_chunk):
        """Подписывается на определенные пары."""
        async with websockets.connect(self.uri) as websocket:
            # создаем подписку на пары
            subscribe_message = {
                "event": "subscribe",
                "pair": pairs_chunk,
                "subscription": {"name": "ticker"}
            }
            await websocket.send(json.dumps(subscribe_message))
            
            logger.info(f"Subscribed to Kraken pairs: {pairs_chunk}")
            
            try:
                async for message in websocket:
                    data = json.loads(message)
                    # Обрабатываем ответ ивент 
                    if isinstance(data, dict) and data.get('event') in ('heartbeat', 'systemStatus', 'subscriptionStatus'):
                        continue  # Игнорируем системные сообщения / в будущем добавить логирование 
                    
                    # Отправляем на обновление цены
                    self.handle_message(data)
            
            except websockets.exceptions.ConnectionClosedError as e:
                # обработчик ошибок 
                logger.error(f"Connection closed with error: {e}. Reconnecting...")
                await asyncio.sleep(5)
                await self.subscribe_to_pairs(pairs_chunk)

    def handle_message(self, data):
        """Обрабатываем полученные данные и обновляет цены."""
        if isinstance(data, list) and len(data) > 1:
            # Нормализует имя текущей пары
            pair = self.normalize_pair(data[-1])
            ticker = data[1]
            
            # Получаем и обновлякем цену
            if isinstance(ticker, dict) and 'b' in ticker and 'a' in ticker:
                # высчитываем среднее значение между покупки и продажи
                self.prices[pair] = (float(ticker['b'][0]) + float(ticker['a'][0])) / 2
                logger.info(f"Kraken updated {pair}: {self.prices[pair]}")
            else:
                logger.warning(f"Invalid ticker data: {ticker}")
        else:
            logger.warning(f"Invalid message format: {data}")

    def normalize_pair(self, pair):
        """Нормализует имя пары."""
        return normalize_pair_name(transform_pair_format(pair.upper()))

async def gather_prices(binance_client, kraken_client):
    """Cобираем цены с бирж Binance и Kraken."""
    await asyncio.gather(
        binance_client.connect(),
        kraken_client.connect()
    )

# Создание приложения
app = FastAPI()

# Создание клиентов
binance_client = BinanceClient()
kraken_client = KrakenClient()

# Старт приложения
@app.on_event("startup")
async def startup_event():
    """Запускаем сбор данных."""
    asyncio.create_task(gather_prices(binance_client, kraken_client))

@app.get("/prices")
async def get_prices(pair: Optional[str] = Query(None), exchange: Optional[str] = Query(None)):
    """Возвращаем цены по указанным параметрам."""
    result = {}
    if exchange:
        if exchange == "binance":
            result["binance"] = binance_client.prices
        elif exchange == "kraken":
            result["kraken"] = kraken_client.prices
    else:
        result["binance"] = binance_client.prices
        result["kraken"] = kraken_client.prices

    if pair:
        normalized_pair = normalize_pair_name(transform_pair_format(pair))
        filtered_result = {ex: {p: val for p, val in pairs.items() if p == normalized_pair} for ex, pairs in result.items()}
        result = {ex: pairs for ex, pairs in filtered_result.items() if pairs}
    
    # Нормализуем названия пар в результатах
    normalized_result = {ex: {normalize_pair_name(transform_pair_format(p)): val for p, val in pairs.items()} for ex, pairs in result.items()}

    #TODO Сортируем пары по сумме от самой большой к самой маленькой
    # sorted_result = {ex: dict(sorted(pairs.items(), key=lambda item: item[1], reverse=True)) for ex, pairs in normalized_result.items()}

    return normalized_result
