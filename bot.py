import pandas as pd
import numpy as np
import ccxt
import time
import requests
import schedule
from flask import Flask

# Criar servidor para manter Railway vivo
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot de Trading Online 🚀"

# Configurações da Binance
exchange = ccxt.binance()

# Configurações do Telegram
TELEGRAM_TOKEN = '7986770725:AAHD3vqPIZNLHvyWVZnrHIT3xGGI1R9ZeoY'
CHAT_ID = '2091781134'

# Função para enviar mensagem no Telegram
def send_telegram_message(message):
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    params = {'chat_id': CHAT_ID, 'text': message}
    requests.get(url, params=params)

# Funções de indicadores
def calculate_ema(data, period):
    return data['close'].ewm(span=period, adjust=False).mean()

def calculate_rsi(data, period):
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# Função de pegar dados
def get_data(symbol, timeframe='1h', limit=100):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    data = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    data['timestamp'] = pd.to_datetime(data['timestamp'], unit='ms')
    return data

# Variáveis globais
symbol = 'BTC/USDT'
stake_usdt = 10
ema_short_period = 9
ema_long_period = 21
rsi_period = 14

position = None
entry_price = 0
stop_loss = 0
take_profit = 0

# Função para verificar sinal
def check_signal():
    global position, entry_price, stop_loss, take_profit

    if position is not None:
        return  # já tem operação aberta

    data = get_data(symbol)
    data['ema_short'] = calculate_ema(data, ema_short_period)
    data['ema_long'] = calculate_ema(data, ema_long_period)
    data['rsi'] = calculate_rsi(data, rsi_period)

    last_row = data.iloc[-1]
    previous_row = data.iloc[-2]

    if last_row['ema_short'] > last_row['ema_long'] and previous_row['ema_short'] <= previous_row['ema_long']:
        entry_price = last_row['close']
        stop_loss = entry_price * 0.995
        take_profit = entry_price * 1.012
        position = 'buy'

        msg = f"""📝 ORDEM ABERTA: {symbol}
Tipo: Compra
Entrada: {entry_price:.2f}
Stop Loss: {stop_loss:.2f}
Take Profit: {take_profit:.2f}
Status: Aberto"""
        send_telegram_message(msg)

# Função para monitorar posição
def monitor_position():
    global position, entry_price, stop_loss, take_profit

    if position is None:
        return

    ticker = exchange.fetch_ticker(symbol)
    current_price = ticker['last']

    if position == 'buy':
        if current_price >= take_profit:
            profit = (take_profit - entry_price) / entry_price * stake_usdt
            msg = f"""✅ Take Profit atingido!
Par: {symbol}
Lucro: +{profit:.2f} USDT"""
            send_telegram_message(msg)
            position = None

        elif current_price <= stop_loss:
            loss = (stop_loss - entry_price) / entry_price * stake_usdt
            msg = f"""❌ Stop Loss atingido!
Par: {symbol}
Prejuízo: {loss:.2f} USDT"""
            send_telegram_message(msg)
            position = None

# Mensagem inicial
send_telegram_message("🤖 Bot de Trading PROFISSIONAL iniciado com sucesso!")

# Agendamento
schedule.every(15).minutes.do(check_signal)
schedule.every(1).minutes.do(monitor_position)

# Loop principal
def run_bot():
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    import threading
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    app.run(host="0.0.0.0", port=3000)
