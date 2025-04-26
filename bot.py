import ccxt
import pandas as pd
import numpy as np
import ta
import time
import telebot
import csv
from datetime import datetime

# 🧠 Configurações do bot
TOKEN = '8165557546:AAEiKshBi7tir2EjAy62NDa7mvXGr4h19Lg'
CHAT_ID = '2091781134'

bot = telebot.TeleBot(TOKEN)
exchange = ccxt.binance()

# 🔍 Pares para acompanhar
symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT']
timeframe = '1h'

open_trades = {}
gain_count = 0
loss_count = 0

# Criar CSV se não existir
csv_file = 'historico_resultados.csv'
try:
    with open(csv_file, 'x', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Data', 'Par', 'Resultado', 'Preço Entrada', 'Preço Fechamento'])
except FileExistsError:
    pass  # Se já existir, passa

def salvar_resultado_csv(par, resultado, preco_entrada, preco_fechamento):
    with open(csv_file, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now().strftime('%Y-%m-%d %H:%M:%S'), par, resultado, preco_entrada, preco_fechamento])

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
    global gain_count, loss_count

    for symbol in symbols:
        df = get_data(symbol)
        last = df.iloc[-1]
        prev = df.iloc[-2]
        price = last['close']

        if symbol not in open_trades:
            # 📈 Entrada de compra
            if prev['EMA9'] < prev['EMA21'] and last['EMA9'] > last['EMA21'] and last['RSI'] > 50:
                sl = price * 0.98
                tp = price * 1.02
                open_trades[symbol] = {'entry': price, 'sl': sl, 'tp': tp, 'time': datetime.now()}
                bot.send_message(CHAT_ID, f'🟢 COMPRA: {symbol}\n💰 Entrada: {price:.2f}\n🎯 TP: {tp:.2f}\n🛑 SL: {sl:.2f}')
            # 🔻 Entrada de venda
            elif prev['EMA9'] > prev['EMA21'] and last['EMA9'] < last['EMA21'] and last['RSI'] < 50:
                sl = price * 1.02
                tp = price * 0.98
                open_trades[symbol] = {'entry': price, 'sl': sl, 'tp': tp, 'time': datetime.now()}
                bot.send_message(CHAT_ID, f'🔴 VENDA: {symbol}\n💰 Entrada: {price:.2f}\n🎯 TP: {tp:.2f}\n🛑 SL: {sl:.2f}')
        else:
            entry = open_trades[symbol]['entry']
            sl = open_trades[symbol]['sl']
            tp = open_trades[symbol]['tp']

            # Verificando se realmente atingiu o TP ou SL
            if (entry < tp and price >= tp) or (entry > tp and price <= tp):
                bot.send_message(CHAT_ID, f'✅ LUCRO: {symbol} atingiu o TP ({tp:.2f})')
                salvar_resultado_csv(symbol, 'LUCRO', entry, price)
                gain_count += 1
                del open_trades[symbol]

            elif (entry < sl and price <= sl) or (entry > sl and price >= sl):
                bot.send_message(CHAT_ID, f'❌ PREJUÍZO: {symbol} atingiu o SL ({sl:.2f})')
                salvar_resultado_csv(symbol, 'PREJUÍZO', entry, price)
                loss_count += 1
                del open_trades[symbol]

            else:
                # Apenas atualiza o status de ordens abertas
                bot.send_message(CHAT_ID, f'📊 {symbol} ainda aberto\nAtual: {price:.2f} | Entrada: {entry:.2f} | SL: {sl:.2f} | TP: {tp:.2f}')

# 🚀 Envia uma única vez a mensagem de início
bot.send_message(CHAT_ID, "🚀 Bot de Trade iniciado com sucesso!\nAguardando sinais...")

# 🔁 Loop infinito para checar sinais
while True:
    check_signals()
    time.sleep(900)  # 15 minutos
