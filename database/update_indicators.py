# imports
import sys,os
sys.path.append("../")
from mongodb import MongoConnection
from utilities import try_request, init_df
import UpsideMomentum
import pandas as pd
import numpy as np
import time
import telegram_send
from datetime import datetime

cols = [
    'timestamp',
    'open',
    'high',
    'low',
    'close',
    'vwap',
    'volume',
    'count'
]

cryptos = [
	'BTC',
	'ETH',
	'LTC',
	'ADA',
	'DOGE',
	'LINK',
	'XLM',
	'ATOM',
	'NEAR',
	'OCEAN',
	'MATIC',
	'DYDX',
	'DOT',
	'UNI',
	'AVAX',
	'FTM',
	'CELR',
	'FET',
	'LRC',
	'MANA',
	'SOL',
	'ALGO',
	'GNO',
	'AKT',
	'RNDR',
	'XMR',
	'XRP',
	'GRT',
	'SHIB',
	'KSM',
	'SUSHI',
	'CQT',
	'HFT',
	'SYN',
	'ARB',
	'OP',
	'LUNA',
	# 'MOON',
	'KAR',
	'SGB',
	'STX',
	'DENT',
	'SEI',
	'COTI',
	'STRK',
	'DYM',
	'JUP',
	'JTO',
	'HNT'
]

def get_metrics(crypto,last_close):
	url = f"https://api.kraken.com/0/public/OHLC?pair={crypto}USD&interval=240"
	response = try_request(url)
	try:
		asset_id = list(response.json()['result'].keys())[0]
	except Exception as err:
		print(err)
		print(response)
		print(response.json())
		return {'close':last_close}
	df = pd.DataFrame(list(response.json()['result'][asset_id]),columns=cols)
	for c in cols:
	    df[c] = df[c].astype('float')
	df['ohlc4'] = (df['open']+df['high']+df['low']+df['close']+df['vwap']) / 5
	# df['ohlc4'] = (df['open']+df['high']+df['low']+df['vwap']) / 4
	um = UpsideMomentum.get_upside_momentum(df)
	vc = UpsideMomentum.get_vc_moneyflow(df)
	avg = np.nan
	if np.isnan(um) == False and np.isnan(vc) == False:
		avg = (um+vc) / 2
	metrics = {
		'symbol':crypto,
		'close':df.iloc[-1]['close'],
		'vwap':df.iloc[-1]['vwap'],
		'um':um,
		'vc':vc,
		'avg':avg
	}
	if avg >= 70 or um >= 80:
		metrics['trade_ready'] = True
	return metrics

def main():
	mdb = MongoConnection()
	while True:
		for crypto in cryptos:
			try:
				last_close = mdb.client.cryptos.find_one({"symbol":crypto})
				if last_close != None:
					last_close = last_close['close']
			except Exception as err:
				print(err)
				print("Refreshing mongo connection...")
				mdb.refresh_connection()
				continue
			# current_close = last_close
			# while current_close == last_close:
			# 	config = get_metrics(crypto)
			# 	current_close = config['close']
			config = get_metrics(crypto,last_close)
			if config['close'] != last_close:
				print(f"{crypto} -> price: {config['close']}")
				print(f"{crypto} -> vwap: {config['vwap']}")
				print(f"{crypto} -> um: {config['um']}")
				print(f"{crypto} -> vc: {config['vc']}")
				print(f"{crypto} -> avg: {config['avg']}")
				print()
				mdb.client.cryptos.update_one({'symbol':config['symbol']},{"$set":config},upsert=True)
			time.sleep(1.1)

if __name__ == '__main__':
	try:
		main()
	except Exception as err:
		message = f"update_indicators has stopped running @ {datetime.now.strftime('%m/%d/%Y, %H:%M:%S')}\n"
		message += err + "\n"
		try:
			print(message)
			print(sys.exc_info()[2])
			telegram_send.send(messages=[message])
		except Exception as terr:
			print(f"Couldn't send telegram message: {terr}")
