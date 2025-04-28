import pandas as pd
import numpy as np
import ccxt
import time
import requests

# Configuração da exchange (Binance)
exchange = ccxt.binance()

# Token do seu bot no Telegram
TELEGRAM_TOKEN = '7986770725:AAHD3vqPIZNLHvyWVZnrHIT3xGGI1R9ZeoY'
# ID do chat do Telegram para onde enviar a mensagem
CHAT_ID = '2091781134'

# Função para calcular EMA
def calculate_ema(data, period):
    return data['close'].ewm(span=period, adjust=False).mean()

# Função para calcular RSI
def calculate_rsi(data, period):
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)

    avg_gain = gain.rolling(window=period, min_periods=1).mean()
    avg_loss = loss.rolling(window=period, min_periods=1).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi

# Função para pegar os dados históricos de preços
def get_data(symbol, timeframe='1h', limit=100):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    data = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    data['timestamp'] = pd.to_datetime(data['timestamp'], unit='ms')
    return data

# Função para enviar uma mensagem via Telegram
def send_telegram_message(message):
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    params = {
        'chat_id': CHAT_ID,
        'text': message
    }
    response = requests.get(url, params=params)
    return response

# Parâmetros para EMA e RSI
ema_short_period = 9
ema_long_period = 21
rsi_period = 14

# Função para formatar as mensagens de ordens abertas
def format_open_order(order_type, price, stop_loss, take_profit):
    return f"📝 ORDEM EM ABERTO: BTC/USDT\nTipo: {order_type}\nEntrada: {price}\nStop Loss: {stop_loss}\nTake Profit: {take_profit}\nStatus: Em andamento"

# Função para formatar as mensagens de ordens fechadas
def format_closed_order(order_type, price, stop_loss, take_profit, profit_loss):
    return f"📝 ORDEM FINALIZADA: BTC/USDT\nTipo: {order_type}\nEntrada: {price}\nStop Loss: {stop_loss}\nTake Profit: {take_profit}\nStatus: {'Lucros' if profit_loss >= 0 else 'Perdas'}\nLucro/Perda: {profit_loss} USDT"

# Enviar mensagem inicial
send_telegram_message("Bot profissional iniciado com múltiplas melhorias.")

# Loop principal
while True:
    # Pegando os dados históricos para o par BTC/USDT
    data = get_data('BTC/USDT')

    # Calculando as EMAs e o RSI
    data['ema_short'] = calculate_ema(data, ema_short_period)
    data['ema_long'] = calculate_ema(data, ema_long_period)
    data['rsi'] = calculate_rsi(data, rsi_period)

    # Verificando a condição de cruzamento de EMAs
    last_row = data.iloc[-1]
    previous_row = data.iloc[-2]

    order_type = None
    order_price = None
    stop_loss = None
    take_profit = None

    if last_row['ema_short'] > last_row['ema_long'] and previous_row['ema_short'] < previous_row['ema_long']:
        order_type = 'Compra'
        order_price = last_row['close']
        stop_loss = order_price - 500  # Ajuste conforme sua estratégia
        take_profit = order_price + 500  # Ajuste conforme sua estratégia
        send_telegram_message(format_open_order(order_type, order_price, stop_loss, take_profit))
        # Adicione seu código de execução de compra aqui, como por exemplo:
        # exchange.create_market_buy_order('BTC/USDT', quantidade)

    elif last_row['ema_short'] < last_row['ema_long'] and previous_row['ema_short'] > previous_row['ema_long']:
        order_type = 'Venda'
        order_price = last_row['close']
        stop_loss = order_price + 500  # Ajuste conforme sua estratégia
        take_profit = order_price - 500  # Ajuste conforme sua estratégia
        send_telegram_message(format_open_order(order_type, order_price, stop_loss, take_profit))
        # Adicione seu código de execução de venda aqui, como por exemplo:
        # exchange.create_market_sell_order('BTC/USDT', quantidade)

    # Aqui, você pode colocar a lógica para verificar se o preço atingiu o stop loss ou take profit
    # Exemplo de como isso pode ser feito:
    # Se o preço atingir o stop loss ou take profit, a ordem será fechada
    # Simulação de fechamento de ordem (essa lógica deve ser ajustada conforme o seu uso real)
    if order_type is not None:
        current_price = last_row['close']  # Substitua por chamada real de preço
        profit_loss = current_price - order_price  # Simulação simples de lucro/perda

        if current_price <= stop_loss or current_price >= take_profit:
            send_telegram_message(format_closed_order(order_type, order_price, stop_loss, take_profit, profit_loss))
            order_type = None  # Resetando a ordem

    # Espera de 15 minutos antes de pegar os novos dados
    time.sleep(900)  # 900 segundos = 15 minutos
