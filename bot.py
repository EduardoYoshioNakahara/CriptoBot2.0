# ====================
# bot.py
# ====================

import ccxt
import pandas as pd
import numpy as np
import ta
import time
import telebot
from datetime import datetime
import csv

# Configurações do bot
TOKEN = '8194783339:AAHa0wW2QiFdvocAwk1vVowOD2QrQRGlD4U'
CHAT_ID = '2091781134'

bot = telebot.TeleBot(TOKEN)
exchange = ccxt.binance()

# Pares para acompanhar
symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT']
timeframe = '1h'

open_trades = {}

# CSV para salvar operações
csv_file = 'operations.csv'
try:
    pd.read_csv(csv_file)
except:
    with open(csv_file, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['datetime', 'symbol', 'type', 'entry', 'result', 'value'])

def log_operation(symbol, type_, entry, result, value):
    with open(csv_file, mode='a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now(), symbol, type_, entry, result, value])

def get_data(symbol):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)

    df['EMA9'] = ta.trend.ema_indicator(df['close'], window=9)
    df['EMA21'] = ta.trend.ema_indicator(df['close'], window=21)
    df['RSI'] = ta.momentum.rsi(df['close'], window=14)

    return df

def check_signals():
    for symbol in symbols:
        df = get_data(symbol)
        last = df.iloc[-1]
        prev = df.iloc[-2]
        price = last['close']

        if symbol not in open_trades:
            # Entrada de compra
            if prev['EMA9'] < prev['EMA21'] and last['EMA9'] > last['EMA21'] and last['RSI'] > 50:
                sl = price * 0.98
                tp = price * 1.02
                open_trades[symbol] = {'entry': price, 'sl': sl, 'tp': tp, 'time': datetime.now(), 'type': 'buy'}
                bot.send_message(CHAT_ID, f'🟢 COMPRA: {symbol}\n💰 Entrada: {price:.2f}\n🎯 TP: {tp:.2f}\n🛡️ SL: {sl:.2f}')
            # Entrada de venda
            elif prev['EMA9'] > prev['EMA21'] and last['EMA9'] < last['EMA21'] and last['RSI'] < 50:
                sl = price * 1.02
                tp = price * 0.98
                open_trades[symbol] = {'entry': price, 'sl': sl, 'tp': tp, 'time': datetime.now(), 'type': 'sell'}
                bot.send_message(CHAT_ID, f'🔴 VENDA: {symbol}\n💰 Entrada: {price:.2f}\n🎯 TP: {tp:.2f}\n🛡️ SL: {sl:.2f}')
        else:
            entry = open_trades[symbol]['entry']
            sl = open_trades[symbol]['sl']
            tp = open_trades[symbol]['tp']
            type_ = open_trades[symbol]['type']

            if type_ == 'buy':
                if price >= tp:
                    bot.send_message(CHAT_ID, f'✅ LUCRO: {symbol} atingiu o TP ({tp:.2f})')
                    log_operation(symbol, 'buy', entry, 'gain', tp)
                    del open_trades[symbol]
                elif price <= sl:
                    bot.send_message(CHAT_ID, f'❌ PREJUÍZO: {symbol} atingiu o SL ({sl:.2f})')
                    log_operation(symbol, 'buy', entry, 'loss', sl)
                    del open_trades[symbol]
                else:
                    bot.send_message(CHAT_ID, f'📊 {symbol} ainda aberto\nAtual: {price:.2f} | Entrada: {entry:.2f} | SL: {sl:.2f} | TP: {tp:.2f}')

            elif type_ == 'sell':
                if price <= tp:
                    bot.send_message(CHAT_ID, f'✅ LUCRO: {symbol} atingiu o TP ({tp:.2f})')
                    log_operation(symbol, 'sell', entry, 'gain', tp)
                    del open_trades[symbol]
                elif price >= sl:
                    bot.send_message(CHAT_ID, f'❌ PREJUÍZO: {symbol} atingiu o SL ({sl:.2f})')
                    log_operation(symbol, 'sell', entry, 'loss', sl)
                    del open_trades[symbol]
                else:
                    bot.send_message(CHAT_ID, f'📊 {symbol} ainda aberto\nAtual: {price:.2f} | Entrada: {entry:.2f} | SL: {sl:.2f} | TP: {tp:.2f}')

# Mensagem de inicio
bot.send_message(CHAT_ID, '🚀 Bot de Trade iniciado com sucesso!\nAguardando sinais...')

# Loop principal
while True:
    check_signals()
    time.sleep(900)  # 15 minutos
