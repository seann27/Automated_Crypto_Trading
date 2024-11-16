# imports
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from utilities import try_request, init_df

def get_calculations(row,suffix=''):
	if row[f'close{suffix}'] == row[f'high{suffix}'] and row[f'close{suffix}'] == row[f'low{suffix}'] or row[f'high{suffix}'] == row[f'low{suffix}']:
		return 0
	else:
		return ((2*row[f'close{suffix}']-row[f'low{suffix}']-row[f'high{suffix}'])/(row[f'high{suffix}']-row[f'low{suffix}']))*row[f'volume{suffix}']

def get_trendline_params(upper,lower):
	if lower == 0:
		return 100
	if upper == 0:
		return 0
	return 100 - (100 / (1 + (upper / lower)))

def get_toptrend_metric(row,metric,suffix=''):
	if row[f'change_{metric}'] <= 0:
		return 0
	else:
		return row[f'volume{suffix}'] * row[metric]

def get_lowertrend_metric(row,metric,suffix=''):
	if row[f'change_{metric}'] >= 0:
		return 0
	else:
		return row[f'volume{suffix}'] * row[metric]

def get_coinbase_data(asset,granularity):
	url = f"https://api.exchange.coinbase.com/products/{asset}/candles?granularity={granularity}"
	response = try_request(url)
	if response == None:
		return None
	suffices = {60: '1m', 300: '5m', 900: '15m', 3600: '1h', 21600: '6h', 86400: '1d'}
	df = init_df(suffix="_"+suffices[granularity])
	for candle in reversed(response.json()):
		timestamp = float(candle[0])
		d = datetime.fromtimestamp(timestamp)
		o = float(candle[3])
		h = float(candle[2])
		l = float(candle[1])
		c = float(candle[4])
		v = float(candle[5])
		temp = pd.DataFrame([[timestamp,d,o,h,l,c,v]], columns=df.columns)
		df = pd.concat([df,temp])

	df.reset_index(inplace=True,drop=True)

	return df

def get_binance_data(asset,interval):
	url = f"https://api.binance.us/api/v3/klines?symbol={asset}&interval={interval}"
	response = try_request(url)
	df = init_df(suffix="_"+interval)
	for candle in response.json():
		timestamp = float(candle[0]/1000)
		d = datetime.fromtimestamp(timestamp)
		o = float(candle[1])
		h = float(candle[2])
		l = float(candle[3])
		c = float(candle[4])
		v = float(candle[5])
		temp = pd.DataFrame([[timestamp,d,o,h,l,c,v]], columns=df.columns)
		df = pd.concat([df,temp])

	df.reset_index(inplace=True,drop=True)

	return df

def get_kucoin_data(asset,interval,start=None,end=None):
	url = f"https://api.kucoin.com/api/v1/market/candles?symbol={asset}&type={interval}"
	if start != None:
		url += f"&startAt={start}"
	if end != None:
		url += f"&endAt={end}"
	response = try_request(url)
	df = init_df()
	for candle in reversed(response.json()['data']):
		timestamp = float(candle[0])
		d = datetime.fromtimestamp(timestamp)
		o = float(candle[1])
		h = float(candle[3])
		l =	float(candle[4])
		c = float(candle[2])
		v = float(candle[5])
		temp = pd.DataFrame([[timestamp,d,o,h,l,c,v]], columns=df.columns)
		df = pd.concat([df,temp])

	df.reset_index(inplace=True)

	return df

def get_backfill_close(row,df,rollnum,suffix):
    if row.name < len(df)-(rollnum-1):
        return df.iloc[row.name+(rollnum-1)][f'close{suffix}']
    else:
        return np.nan

def get_backfill_open(row,df,rollnum,suffix):
	if row.name >= rollnum:
		return df.iloc[row.name-rollnum][f'close{suffix}']
	else:
		return np.nan

# def backfill_data(df,rollnum,srcsuffix,bfsuffix):
# 	# df[f'open{bfsuffix}'] = df[f'open{srcsuffix}']
# 	df[f'open{bfsuffix}'] = df.apply(lambda row: get_backfill_open(row,df,rollnum,srcsuffix),axis=1)
# 	df[f'close{bfsuffix}'] = df[f'close{srcsuffix}']
# 	# df[f'high{bfsuffix}'] = df.iloc[::-1].rolling(rollnum)[f'high{srcsuffix}'].max()
# 	# df[f'low{bfsuffix}'] = df.iloc[::-1].rolling(rollnum)[f'low{srcsuffix}'].min()
# 	# df[f'volume{bfsuffix}'] = df.iloc[::-1].rolling(rollnum)[f'volume{srcsuffix}'].sum()
# 	df[f'high{bfsuffix}'] = df[f'high{srcsuffix}'].rolling(rollnum).max()
# 	df[f'low{bfsuffix}'] = df[f'low{srcsuffix}'].rolling(rollnum).min()
# 	df[f'ohlc4{bfsuffix}'] = (df[f'open{bfsuffix}'] + df[f'high{bfsuffix}'] + df[f'low{bfsuffix}'] + df[f'close{bfsuffix}']) / 4
# 	df[f'volume{bfsuffix}'] = df[f'volume{srcsuffix}'].rolling(rollnum).sum()
# 	df[f'volquote{bfsuffix}'] = df[f'volquote{srcsuffix}'].rolling(rollnum).sum()
#
# 	return df

def backfill_data(df,rollnum,srcsuffix,bfsuffix):
    df[f'open_{bfsuffix}'] = df[f'open_{srcsuffix}']
    df[f'close_{bfsuffix}'] = df.apply(lambda row: get_backfill_close(row,df,rollnum,srcsuffix),axis=1)
    df[f'high_{bfsuffix}'] = df.iloc[::-1].rolling(rollnum)[f'high_{srcsuffix}'].max()
    df[f'low_{bfsuffix}'] = df.iloc[::-1].rolling(rollnum)[f'low_{srcsuffix}'].min()
    df[f'ohlc4_{bfsuffix}'] = (df[f'open_{bfsuffix}'] + df[f'high_{bfsuffix}'] + df[f'low_{bfsuffix}'] + df[f'close_{bfsuffix}']) / 4
    df[f'volume_{bfsuffix}'] = df.iloc[::-1].rolling(rollnum)[f'volume_{srcsuffix}'].sum()
    df[f'volquote_{bfsuffix}'] = df[f'volquote_{srcsuffix}'].rolling(rollnum).sum()

    return df

def get_upside_momentum(df,suffix='',return_df=False,return_series=False):

	# df[f'ohlc4{suffix}'] = (df[f'open{suffix}']+df[f'high{suffix}']+df[f'low{suffix}']+df[f'close{suffix}'])/4
	df[f'change_ohlc4{suffix}'] = df[f'ohlc4{suffix}'] - df[f'ohlc4{suffix}'].shift(1)
	df[f'change_close{suffix}'] = df[f'close{suffix}'] - df[f'close{suffix}'].shift(1)
	df[f'calculations{suffix}'] = df.apply(lambda row: get_calculations(row,suffix),axis=1)
	df[f'trendstrength{suffix}'] = df[f'calculations{suffix}'].rolling(1).sum() / df[f'volume{suffix}'].rolling(1).sum()
	df[f'ttmet1{suffix}'] = df.apply(lambda row: get_toptrend_metric(row,f'ohlc4{suffix}',suffix),axis=1)
	df[f'ttmet2{suffix}'] = df.apply(lambda row: get_toptrend_metric(row,f"close{suffix}",suffix),axis=1)
	df[f'ltmet1{suffix}'] = df.apply(lambda row: get_lowertrend_metric(row,f'ohlc4{suffix}',suffix),axis=1)
	df[f'ltmet2{suffix}'] = df.apply(lambda row: get_lowertrend_metric(row,f"close{suffix}",suffix),axis=1)
	df[f'toptrend{suffix}'] = df[f'ttmet1{suffix}'].rolling(8).sum()
	df[f'lowertrend{suffix}'] = df[f'ltmet1{suffix}'].rolling(8).sum()
	df[f'toptrend2{suffix}'] = df[f'ttmet2{suffix}'].rolling(8).sum()
	df[f'lowertrend2{suffix}'] = df[f'ltmet2{suffix}'].rolling(8).sum()
	df[f'trendline{suffix}'] = df.apply(lambda row: get_trendline_params(row[f'toptrend{suffix}'],row[f'lowertrend{suffix}']),axis=1)
	df[f'trendline2{suffix}'] = df.apply(lambda row: get_trendline_params(row[f'toptrend2{suffix}'],row[f'lowertrend2{suffix}']),axis=1)
	df[f'upside_momentum{suffix}'] = df[f'trendline{suffix}'] + (df[f'trendstrength{suffix}']/df[f'trendline2{suffix}']) + df[f'trendstrength{suffix}']

	upside_momentum = df.iloc[-1][f'upside_momentum{suffix}']
	if upside_momentum == float('-inf') or upside_momentum == float('inf'):
		upside_momentum = np.nan

	# if np.isnan(upside_momentum):
	# 	print(f"**** Bad data for {symbol} - {interval} ****\n")
	df[f'upside_momentum{suffix}'] = df[f'upside_momentum{suffix}'].replace(to_replace=float('inf'),method='ffill')
	df[f'upside_momentum{suffix}'] = df[f'upside_momentum{suffix}'].replace(to_replace=float('-inf'),method='ffill')

	if return_df:
		return df

	if return_series:
		return df[f'upside_momentum{suffix}']

	return upside_momentum

def get_vc_moneyflow(df,suffix='',return_df=False, return_series=False):

	df[f'adjustment{suffix}'] = df.apply(lambda row: get_calculations(row,suffix),axis=1)
	df[f'vcmfi{suffix}'] = df[f'adjustment{suffix}'].rolling(10).sum() / df[f'volume{suffix}'].rolling(10).sum()
	df[f'mst{suffix}'] = df.apply(lambda row: get_toptrend_metric(row,f"close{suffix}",suffix),axis=1)
	df[f'msb{suffix}'] = df.apply(lambda row: get_lowertrend_metric(row,f"close{suffix}",suffix),axis=1)
	df[f'mst2{suffix}'] = df[f'mst{suffix}'].rolling(14).sum()
	df[f'msb2{suffix}'] = df[f'msb{suffix}'].rolling(14).sum()
	df[f'vcstrength{suffix}'] = df.apply(lambda row: get_trendline_params(row[f'mst2{suffix}'],row[f'msb2{suffix}']),axis=1)
	df[f'vc_moneyflow{suffix}'] = df[f'vcstrength{suffix}'] + df[f'vcmfi{suffix}']

	df[f'vc_moneyflow{suffix}'] = df[f'vc_moneyflow{suffix}'].replace(to_replace=float('inf'),method='ffill')
	df[f'vc_moneyflow{suffix}'] = df[f'vc_moneyflow{suffix}'].replace(to_replace=float('-inf'),method='ffill')

	if return_df:
		return df
	elif return_series:
		return df[f'vc_moneyflow{suffix}']
	else:
		vc_moneyflow = df.iloc[-1][f'vc_moneyflow{suffix}']
		if vc_moneyflow == float('-inf') or vc_moneyflow == float('inf'):
			vc_moneyflow = np.nan

	return vc_moneyflow

def get_fibopivots(df,suffix='',return_df=False):
	df[f'pivot{suffix}'] = (df[f'high{suffix}'].shift(1)+df[f'low{suffix}'].shift(1)+df[f'close{suffix}'].shift(1))/3
	df[f's1{suffix}'] = df[f'pivot{suffix}'] - (0.382 * (df[f'high{suffix}'] - df[f'low{suffix}']))
	df[f's2{suffix}'] = df[f'pivot{suffix}'] - (0.618 * (df[f'high{suffix}'] - df[f'low{suffix}']))

	if return_df:
		df[f'pivot{suffix}'] = df[f'pivot{suffix}'].replace(to_replace=float('inf'),method='ffill')
		df[f's1{suffix}'] = df[f's1{suffix}'].replace(to_replace=float('inf'),method='ffill')
		df[f's2{suffix}'] = df[f's2{suffix}'].replace(to_replace=float('inf'),method='ffill')
		df[f'pivot{suffix}'] = df[f'pivot{suffix}'].replace(to_replace=float('-inf'),method='ffill')
		df[f's1{suffix}'] = df[f's1{suffix}'].replace(to_replace=float('-inf'),method='ffill')
		df[f's2{suffix}'] = df[f's2{suffix}'].replace(to_replace=float('-inf'),method='ffill')
		return df
	else:
		pivot = df.iloc[-1][f'pivot{suffix}']
		if pivot == float('-inf') or pivot == float('inf'):
			pivot = np.nan
		s1 = df.iloc[-1][f's1{suffix}']
		if s1 == float('-inf') or s1 == float('inf'):
			s1 = np.nan
		s2 = df.iloc[-1][f's2{suffix}']
		if s2 == float('-inf') or s2 == float('inf'):
			s2 = np.nan
		return pivot,s1,s2
