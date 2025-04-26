import ccxt
import pandas as pd
import ta
import time
import telebot
import os
from datetime import datetime
import csv

# 🔥 Configurações do Bot
TOKEN = '8194783339:AAHa0wW2QiFdvocAwk1vVowOD2QrQRGlD4U'
CHAT_ID = '2091781134'

bot = telebot.TeleBot(TOKEN)
exchange = ccxt.binance()

symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT']
timeframe = '1h'

open_trades = {}
csv_filename = 'trades_resultados.csv'

# 🧹 Cria o CSV se não existir
if not os.path.exists(csv_filename):
    with open(csv_filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Data', 'Par', 'Resultado', 'Preço Entrada', 'Preço Saída'])

def get_data(symbol):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df['EMA9'] = ta.trend.ema_indicator(df['close'], window=9)
    df['EMA21'] = ta.trend.ema_indicator(df['close'], window=21)
    df['RSI'] = ta.momentum.rsi(df['close'], window=14)
    return df

def salvar_resultado(par, resultado, preco_entrada, preco_saida):
    with open(csv_filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), par, resultado, f"{preco_entrada:.2f}", f"{preco_saida:.2f}"])

def check_signals():
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

            # Se atingir o TP
            if (entry < tp and price >= tp) or (entry > tp and price <= tp):
                bot.send_message(CHAT_ID, f'✅ LUCRO: {symbol} atingiu o TP ({tp:.2f})')
                salvar_resultado(symbol, 'Lucro', entry, price)
                del open_trades[symbol]

            # Se atingir o SL
            elif (entry < sl and price <= sl) or (entry > sl and price >= sl):
                bot.send_message(CHAT_ID, f'❌ PREJUÍZO: {symbol} atingiu o SL ({sl:.2f})')
                salvar_resultado(symbol, 'Prejuízo', entry, price)
                del open_trades[symbol]

            # Se não atingiu TP nem SL, atualiza a cada 15min
            else:
                bot.send_message(CHAT_ID, f'📊 {symbol} ainda aberto\nAtual: {price:.2f} | Entrada: {entry:.2f} | SL: {sl:.2f} | TP: {tp:.2f}')

# 🚀 Envia apenas 1x no início
bot.send_message(CHAT_ID, "🚀 Bot de Trade iniciado com sucesso!\nAguardando sinais...")

# Loop principal
while True:
    try:
        check_signals()
    except Exception as e:
        bot.send_message(CHAT_ID, f"⚠️ Erro no bot: {str(e)}")
    time.sleep(900)  # 15 minutos
