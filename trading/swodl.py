import sys,os
sys.path.append("../database/")
from mongodb import MongoConnection
import pymongo
import krakenex
import re
from math import floor
import telegram_send
from datetime import datetime
import time
import traceback
import subprocess
# telegram_send.send(messages=["message goes here"])

class SwodlBot:

	def __init__(self,settings_id=1):
		# api key
		api_key = os.environ['KRAKEN_API_KEY']
		# secret key
		secret_key = os.environ['KRAKEN_API_SECRET']
		self.api = krakenex.API(key=api_key,secret=secret_key)
		self.mdb = MongoConnection()
		self.settings_cfg = settings_id
		self.settings = self.mdb.client.settings.find_one({"config_id":settings_id})

	def update_settings(self,config=None,update_balance=False):
		if update_balance == True:
			response = self.api.query_private('BalanceEx')
			if 'result' not in response.keys():
				print(response['error'])
				time.sleep(60)
				response = self.api.query_private('BalanceEx')
			balance = float(response['result']['ZUSD']['balance']) - float(response['result']['ZUSD']['hold_trade'])
			# update balance
			if config == None:
				config = {"balance":balance}
			else:
				config["balance"] = balance
			self.mdb.client.settings.update_one({"config_id":self.settings_cfg},{"$set":config},upsert=True)
			time.sleep(3)
		self.settings = self.mdb.client.settings.find_one({"config_id":self.settings_cfg})

	def execute_buy(self,sym):
		config = {
			'pair':sym+'USD',
			'type':'buy',
			'ordertype':'market',
			'volume':self.settings['cash_per_trade'],
			'oflags':'viqc'
		}
		response = self.api.query_private('AddOrder',config)
		if 'result' not in response.keys():
			print("Something went wrong executing buy order")
			print(config)
			if 'error' in response.keys():
				print(response['error'])
		txnid = response['result']['txid'][0]
		time.sleep(5)
		self.update_settings(update_balance=True)
		return txnid

	def open_trade(self,sym,txnid=None):
		if txnid == None:
			txnid = self.execute_buy(sym)
		order = self.api.query_private('QueryOrders',{'txid':txnid})
		if 'error' in order.keys():
			if order['error'] != []:
				print(order['error'])
		order = order['result'][txnid]
		# function that takes txn id as input, stores in mongo
		trade = {
			'tradeid':sym+"-"+str(floor(order['opentm'])),
			'symbol':sym,
			'pair':order['descr']['pair'],
			'open_timestamp':floor(order['opentm']),
			'open_price':float(order['price']),
			'open_amount':float(order['vol_exec']),
			'open_cost':float(order['cost']),
			'open_fees':float(order['fee']),
			'open_txns':[txnid],
			'status':"open",
			'close_timestamp':None,
			'close_price':None,
			'close_fees':None,
			'close_sale':None,
			'close_txn':None
		}
		self.mdb.client.trades.update_one({'tradeid':trade['tradeid']},{"$set":trade},upsert=True)
		self.mdb.client.cryptos.update_one({'symbol':sym},{'$set':{'trade_ready':False}},upsert=True)
		message = f"Opened {trade['tradeid']} @ {datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}\n"
		message += f"Price: {trade['open_price']}\n"
		message += f"Amount: {trade['open_amount']}\n"
		message += f"Cost: {trade['open_cost']}\n"
		message += f"Fees: {trade['open_fees']}\n"
		print(message)
		telegram_send.send(messages=[message])
		if self.settings['consolidate_trades'] is True:
			self.consolidate(sym)
		time.sleep(3)

	def execute_sell(self,sym,vol):
		config = {
			'pair':sym+'USD',
			'type':'sell',
			'ordertype':'market',
			'volume':float(vol)*0.995,
		}
		response = self.api.query_private('AddOrder',config)
		if 'result' not in response.keys():
			print("Something went wrong executing sell order")
			print(config)
			if 'error' in response.keys():
				print(response['error'])
		txnid = response['result']['txid'][0]
		time.sleep(5)
		self.update_settings(update_balance=True)
		return txnid

	def close_trade(self,tradeid,txnid=None):
		trade = self.mdb.client.trades.find_one({"tradeid":tradeid})
		if txnid == None:
			txnid = self.execute_sell(trade['symbol'],trade['open_amount'])
		api_attempts = 0
		while api_attempts < 5:
			trade_sale = self.api.query_private('QueryOrders',{'txid':txnid})
			if txnid in trade_sale['result'].keys():
				api_attempts = 5
			else:
				api_attempts += 1
				time.sleep(6)
		trade_sale = trade_sale['result'][txnid]

		# tradeid = trade['tradeid']
		cost = trade['open_cost']
		closing_trade = {
			'status':"closed",
			'close_timestamp':floor(trade_sale['opentm']),
			'close_price':float(trade_sale['price']),
			'close_fees':float(trade_sale['fee']),
			'close_sale':float(trade_sale['cost']),
			'close_txn':'O7EXIR-T5UMR-G2J6M3',
			"profit": "{:.2f}".format(float(trade_sale['cost']) - float(cost)),
			"pct_profit": "{:.2f}%".format(((float(trade_sale['cost']) - float(cost)) / float(cost)) * 100)
		}
		self.mdb.client.trades.update_one({'tradeid':tradeid},{"$set":closing_trade},upsert=True)
		message = "### TRADE CLOSED! ###\n"
		message += trade['symbol']+"\n"
		message += f"Trade ID: {trade['tradeid']}\n"
		message += "Investment: ${:.2f}\n".format(float(trade['open_cost']))
		message += "Sale: ${:.2f}\n".format(float(trade_sale['cost']))
		message += "Open: ${:.2f}\n".format(float(trade['open_price']))
		message += "Close: ${:.2f}\n".format(float(trade_sale['price']))
		message += "Profit: ${:.2f}\n".format(float(trade_sale['cost']) - float(cost))
		message += "+{:.2f}%\n".format(((float(trade_sale['cost']) - float(cost)) / float(cost)) * 100)
		print(message)
		telegram_send.send(messages=[message])
		time.sleep(3)

	def scan_for_open(self):
		buy_conditions = [
			{"trade_ready":True},
			{"$or":[{"avg":{"$lte":self.settings['combined_buy_threshold']}},{"um":{"$lte":self.settings['um_buy_threshold']}}]},
		]
		if self.settings['use_vwap'] is True:
			buy_conditions.append({"$expr":{"$gt": ["vwap","close"]}})
		trade_ready = list(self.mdb.client.cryptos.find({"$and":buy_conditions}))
		open_trades = []
		for tr in trade_ready:
			active_trades = list(self.mdb.client.trades.find({"$and":[{'symbol':tr['symbol']},{"status":"open"}]}))
			if len(active_trades) < self.settings['consolidation_limit']:
				open_trades.append(tr)
		return open_trades

	def scan_for_close(self):
		sell_conditions = [
			{"$or":[{"avg":{"$gte":self.settings['combined_sell_threshold']}},{"um":{"$gte":self.settings['um_sell_threshold']}}]},
		]
		if self.settings['use_vwap'] is True:
			sell_conditions.append({"$expr":{"$lt": ["vwap","close"]}})
		trade_ready = list(self.mdb.client.cryptos.find({"$and":sell_conditions}))
		closing_trades = []
		for tr in trade_ready:
			t = list(self.mdb.client.trades.find({"$and":[{'symbol':tr['symbol']},{"status":"open"}]}))
			for order in t:
				pair = list(self.api.query_public('Ticker',{'pair':tr['symbol']+'USD'})['result'].keys())[0]
				bids = self.api.query_public('Ticker',{'pair':tr['symbol']+'USD'})['result'][pair]['b']
				if float(bids[0]) > float(order['open_price'])*(1+self.settings['take_profit']):
					closing_trades.append(order)
					print("Closing trade found")
					print(tr)
					print(order)
					print()
				time.sleep(0.5)
		return closing_trades

	def consolidate(self,sym):
		timestamp = floor(datetime.now().timestamp())
		open_trades = list(self.mdb.client.trades.find({"$and":[{"symbol":sym},{"status":"open"}]}))
		if len(open_trades) > 1:
			new_trade = {"pair":open_trades[0]['pair'],"symbol":sym,"status":"open"}
			new_trade['tradeid'] = sym+"-"+str(timestamp)
			new_trade['open_timestamp'] = timestamp
			total_amount = 0
			total_cost = 0
			total_fees = 0
			total_txns = []
			for o in open_trades:
				del o['_id']
				o['status'] = 'consolidated'
				# update database for trade
				total_amount += o['open_amount']
				total_cost += o['open_cost']
				total_fees += o['open_fees']
				total_txns += o['open_txns']
			new_trade['open_amount'] = total_amount
			new_trade['open_cost'] = total_cost
			new_trade['open_price'] = total_cost / total_amount
			new_trade['open_fees'] = total_fees
			new_trade['open_txns'] = total_txns

			for o in open_trades:
				print(o)
				self.mdb.client.trades.update_one({"tradeid":o['tradeid']},{"$set":o},upsert=True)
			self.mdb.client.trades.update_one({"tradeid":new_trade['tradeid']},{"$set":new_trade},upsert=True)
			print()
			print(new_trade)
		else:
			print(f"No open trades to consolidate for {sym}")

	def run_bot(self):
		self.update_settings(update_balance=True)
		while self.settings['run_bot'] == True:
			try:
				self.update_settings()
				if self.settings['balance'] >= self.settings['cash_per_trade']:
					available_trades = self.scan_for_open()
					for at in available_trades:
						self.open_trade(at['symbol'])
						break
				finished_trades = self.scan_for_close()
				for ft in finished_trades:
					self.close_trade(ft['tradeid'])
			except Exception as err:
				print(f"An error as occurred @ {datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}\n")
				time.sleep(30)

			time.sleep(5)

if __name__ == '__main__':
	try:
		bot = SwodlBot()
		bot.run_bot()
	except Exception as err:
		message = f"swodl bot has stopped running @ {datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}\n"
		message += str(err) + "\n"
		try:
			print(message)
			print(traceback.format_exc())
			telegram_send.send(messages=[message])
			if type(Exception) == pymongo.errors.AutoReconnect():
				print("Attempting to establish fresh mongo connection...")
				time.sleep(30)
				bot.mdb.refresh_connection()
		except Exception as terr:
			print(f"Couldn't send telegram message: {str(terr)}")
			print(traceback.format_exc())
