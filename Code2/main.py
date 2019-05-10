# -*- coding: utf-8 -*-
# Time: 9/5/2018 11:24 PM
# Author: Guanlin Chen
from datetime import datetime, timedelta
import pandas as pd
from time import sleep
import ccxt
from Code.Trade import next_run_time, place_order, get_bitfinex_candle_data, auto_send_email, fetch_position, send_dingding_msg,fetch_margin_balance
from Code.Signals import signal_bolling
pd.set_option('display.max_rows', 1000)
pd.set_option('expand_frame_repr', False)  # 当列太多时不换行

"""

"""

# =====参数
time_interval = '30m'  # 间隔运行时间
exchange = ccxt.bitfinex()
exchange2 = ccxt.bitfinex2()  # 创建交易所，此处为okex交易所
exchange.apiKey = 'your key'
exchange.secret = 'your secret'
exchange2.apiKey = 'your key'
exchange2.secret = 'your secret'

symbol = 'EOS/USDT'  # 交易品种
symbol_for_position = 'eosusd'
base_coin = symbol.split('/')[-1]
trade_coin = symbol.split('/')[0]
leverage = 2
para = [300, 3.4]  # 策略参数
email = 'chenguanlin@hotmail.com'
# =====主程序
while True:
    # ===监控邮件内容
    email_title = '策略报表'
    email_content = 'eos'

    # ===从服务器更新账户balance信息
    # balance = exchange.fetch_balance()['total']
    margin_balance = fetch_margin_balance(exchange, symbol)
    position = fetch_position(exchange, symbol_for_position)
    # base_coin_amount = float(balance[base_coin])
    # trade_coin_amount = float(balance[trade_coin])
    # print('当前资产:\n', base_coin, base_coin_amount, trade_coin, trade_coin_amount)
    # exit()
    # # ===sleep直到运行时间
    run_time = next_run_time(time_interval)
    sleep(max(0, (run_time - datetime.now()).seconds))
    while True:  # 在靠近目标时间时
        if datetime.now() < run_time:
            continue
        else:
            break

    # ===check the data if it is newest
    while True:
        # 获取数据
        df = get_bitfinex_candle_data(exchange, symbol, time_interval)
        # 判断是否包含最新的数据
        _temp = df[df['candle_begin_time_GMT8'] == (run_time - timedelta(minutes=int(time_interval.strip('m'))))]
        if _temp.empty:
            print('did not include the newest data，fetching again')
            sleep(5)
            continue
        else:
            break

    # === producing trading signal
    df = df[df['candle_begin_time_GMT8'] < pd.to_datetime(run_time)]  # 去除target_time周期的数据
    df = signal_bolling(df, para=para)
    # print(df)
    # exit()
    signal = df.iloc[-1]['signal']
    # signal = -1  # 测试用
    print('\n交易信号', signal)

    # =====No position and sell short
    if margin_balance > 0 and signal == -1 and position == 0:
        print('\n卖出')
        # 获取最新的卖出价格
        price = exchange.fetch_ticker(symbol)['bid']  # 获取买一价格
        sell_amount = (margin_balance * leverage) / price
        # 下单
        place_order(exchange, order_type='limit', buy_or_sell='sell', symbol=symbol, price=price * 0.98,
                    amount=sell_amount)
        # 邮件标题
        email_title += '_卖出_' + trade_coin
        # 邮件内容
        email_content += '卖出信息：\n'
        email_content += '卖出数量：' + str(sell_amount) + '\n'
        email_content += '卖出价格：' + str(price) + '\n'
        auto_send_email(email, 'Sell short', email_content)

    # =====空仓买入
    if margin_balance > 0 and signal == 1 and position == 0:
        print('\n买入')
        # 获取最新的买入价格
        price = exchange.fetch_ticker(symbol)['ask']  # 获取卖一价格
        # 计算买入数量
        buy_amount = leverage * margin_balance / price
        # 获取最新的卖出价格
        place_order(exchange, order_type='limit', buy_or_sell='buy', symbol=symbol, price=price * 1.02,
                    amount=buy_amount)
        # 邮件标题
        email_title += '_买入_' + trade_coin
        # 邮件内容
        email_content += '买入信息：\n'
        email_content += '买入数量：' + str(buy_amount) + '\n'
        email_content += '买入价格：' + str(price) + '\n'
        auto_send_email(email, 'Buy long', email_content)
    # =====close short and long buy
    if signal == 1 and position < 0:
        print('\n买入')
        # 获取最新的买入价格
        price = exchange.fetch_ticker(symbol)['ask']  # 获取卖一价格
        # 计算买入数量
        buy_amount1 = position * -1
        buy_amount2 = leverage * margin_balance / price
        # 获取最新的卖出价格
        place_order(exchange, order_type='limit', buy_or_sell='buy', symbol=symbol, price=price * 1.02,
                    amount=buy_amount1)
        place_order(exchange, order_type='limit', buy_or_sell='buy', symbol=symbol, price=price * 1.02,
                    amount=buy_amount2)
        # 邮件标题
        email_title += '_买入_' + trade_coin
        # 邮件内容
        email_content += '买入信息：\n'
        email_content += '买入数量：' + str(buy_amount1) + '\n'
        email_content += '买入价格：' + str(price) + '买入平仓' + '\n'
        email_content += '买入数量：' + str(buy_amount2) + '重新开仓' + ' ' + '\n'
        email_content += '买入价格：' + str(price) + '\n'
        auto_send_email(email, 'close short and long buy', email_content)

    # =====close long and sell short
    if signal == -1 and position > 0:
        print('\n卖出')
        # 获取最新的卖出价格
        price = exchange.fetch_ticker(symbol)['bid']  # 获取买一价格
        sell_amount1 = position
        sell_amount2 = (margin_balance * leverage) / price
        # 下单
        place_order(exchange, order_type='limit', buy_or_sell='sell', symbol=symbol, price=price * 0.98,
                    amount=sell_amount1)
        place_order(exchange, order_type='limit', buy_or_sell='sell', symbol=symbol, price=price * 0.98,
                    amount=sell_amount2)
        # 邮件标题
        email_title += '_卖出_' + trade_coin
        # 邮件内容
        email_content += '卖出信息：\n'
        email_content += '卖出数量：' + str(sell_amount1) + '卖出平仓' + ' ' + '\n'
        email_content += '卖出价格：' + str(price) + '\n'
        email_content += '卖出数量：' + str(sell_amount2) + '重新开仓' + ' ' + '\n'
        email_content += '卖出价格：' + str(price) + '\n'
        auto_send_email(email, 'close long and sell short', email_content)
    # close short position
    if signal == 0 and position < 0:
        print('\n买入')
        # 获取最新的买入价格
        price = exchange.fetch_ticker(symbol)['ask']  # 获取卖一价格
        # 计算买入数量
        buy_amount = position * -1
        # 获取最新的卖出价格
        place_order(exchange, order_type='limit', buy_or_sell='buy', symbol=symbol, price=price * 1.02,
                    amount=buy_amount)
        # 邮件标题
        email_title += '_买入_' + trade_coin
        # 邮件内容
        email_content += '买入信息：\n'
        email_content += '买入数量：' + str(buy_amount) + '买入平仓' + '\n'
        email_content += '买入价格：' + str(price) + '\n'
        auto_send_email(email, 'close short position', email_content)
    # close long position
    if signal == 0 and position > 0:
        print('\n卖出')
        # 获取最新的卖出价格
        price = exchange.fetch_ticker(symbol)['bid']  # 获取买一价格
        sell_amount = position
        # 下单
        place_order(exchange, order_type='limit', buy_or_sell='sell', symbol=symbol, price=price * 0.98,
                    amount=sell_amount)
        # 邮件标题
        email_title += '_卖出_' + trade_coin
        # 邮件内容
        email_content += '卖出信息：\n'
        email_content += '卖出数量：' + str(sell_amount) + '卖出平仓' + '\n'
        email_content += '卖出价格：' + str(price) + '\n'
        auto_send_email(email, 'close long position', email_content)

    # =====sending email
    # sending the report to dingding every 30 min
    if run_time.minute % 30 == 0:
        # 发送邮件
        send_dingding_msg(email_content)

    # =====trading close
    print(email_title)
    print(email_content)
    print('=====本次运行完毕\n')
    sleep(60 * 10)