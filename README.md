# Test Task for the Position of Back-End Python Developer

## Task Description

Develop a comprehensive application (API service) that retrieves real-time price data from multiple crypto exchanges, including Binance and Kraken.

## Requirements:

1. Create an API service in Python 3.x using the FastAPI framework.
2. Implement a WebSocket connection to retrieve price data.
3. The application should provide an interface to fetch data for any currency pair from the specified exchanges.
4. Include two filters or parameters: pair (nullable) and exchange (nullable).
5. If neither the pair nor the exchange is specified, display all prices from both exchanges, considering aggregation
6. If only the exchange is specified, show all prices from that particular exchange.
7. If both the exchange and pair are specified, display prices for the specified pair.
8. The application should not rely on REST API or make real-time requests at the time of the API service call.*
9. Deploy the application using Docker.
10. The application should not require a database or save any data.

## Additional Details:

1. The crypto exchanges have different trading pairs, such as BTC_USDT, ETH_USDT, and more.
2. Each trading pair has a buy and sell price. Calculate the average value between these two prices for each pair.
3. The API service should provide prices for all trading pairs available on the exchanges.
4. Take into account that the pair names may vary across exchanges. Normalize the pair names to a common format.

## Implementation

###The implementation consists of three main parts:
**WebSocket Clients for Binance and Kraken**
**FastAPI application**
**Docker setup**

### 1. WebSocket Clients

**BinanceClient** and **KrakenClient** are used to connect to the respective exchanges via WebSocket, retrieve price data, and normalize it.

### 2. FastAPI Application

The FastAPI application creates endpoints to retrieve the price data. It supports filtering by `pair` and `exchange`.

### 3. Docker Setup

Docker is used to containerize the application for easy deployment.

## Files

1. **main.py** - The main application code
2. **Dockerfile** - Docker configuration for building the application
3. **docker-compose.yml** - Docker Compose configuration

## How to Run

### Build the Docker image:

```bash
docker-compose build
```

### Run the application:

```bash
docker-compose up
```

## Examples

### Get all prices from both exchanges:

```bash
GET http://localhost:8000/prices
```

### Get all prices from Binance:

```bash
GET http://localhost:8000/prices?exchange=binance
```

### Get price for a specific pair on Kraken:

```bash
GET http://localhost:8000/prices?pair=BTC/USD&exchange=kraken
```

This completes the setup and usage instructions for the test task.
