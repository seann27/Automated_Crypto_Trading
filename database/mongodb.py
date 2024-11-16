from pymongo import MongoClient
import certifi
import os
from datetime import datetime

assets = [
	'BTCUSD',
	'ETHUSD',
	'LTCUSD',
	'ADAUSD',
	'DOGEUSD',
	'LINKUSD',
	'XLMUSD',
	'ATOMUSD',
	'ALGOUSD',
	'BNBUSD',
	'MATICUSD',
	'AAVEUSD',
	'DOTUSD',
	'UNIUSD',
	'AVAXUSD'
]

class MongoConnection:

	def __init__(self):
		self.client = self.connect()

	def connect(self):
	    username = os.environ['CRYPTODB_USER']
	    password = os.environ['CRYPTODB_PASS']
	    database = os.environ['CRYPTODB_DB']
	    dbname = os.environ['CRYPTODB_DBNAME']
	    dburi = os.environ['CRYPTODB_URI']

	    ca = certifi.where()
	    client = MongoClient(f"mongodb+srv://{username}:{password}@{dburi}/{database}?retryWrites=true&w=majority",tlsCAFile=ca)
	    return client[dbname]

	def refresh_connection(self):
		self.client.close()
		self.client = self.connect()

	def reset_db(self):
		for a in assets:
			config = {
				"asset":a,
				"price":0,
				"um_4h":0,
				"rsi_4h":0,
				"vc_mfi_4h":0,
				"buy_signal":0,
				"sell_signal":0,
				"last_updated":datetime.now()
			}
			self.client.assets.update_one({'asset':a},{"$set":config},upsert=True)

	def get_assets(self):
		assets = []
		results = self.client.assets.find()
		for r in results:
			assets.append(r)
		return assets

	def get_asset(self,symbol):
		return self.client.assets.find_one({"symbol":symbol})

	def add_bot(self,name,starting_balance,xfac=0.12,max_trades=3,buy_thresholds=[1.032,1],sell_thresholds=[1,0.968],um_thresholds=[80,20]):
		bot = {
			'name': name,
			'starting_capital':starting_balance,
			'cash':starting_balance,
			'assets':0,
			'funds_in_trade':0,
			'wins':0,
			'losses':0,
			'created_timestamp':datetime.now(),
			'last_updated':datetime.now(),
			'status':'idle',
			'trades':[],
			'max_trades':max_trades,
			'buy_thresholds':buy_thresholds,
			'sell_thresholds':sell_thresholds,
			'um_thresholds':um_thresholds
		}
		# self.client.bots.update_one({'name':name},{"$set":bot},upsert=True)
		_id = self.client.bots.insert_one(bot)
		return _id.inserted_id

	def update_bot(self,config):
		name = config['name']
		config['last_updated'] = datetime.now()
		self.client.bots.update_one({"name":name},{"$set":config})

	def add_trade(self,symbol,botid,cash,cash_per_purchase):
		trade = {
			'created_time':datetime.now(),
			'last_updated':datetime.now(),
			'botid':botid,
			'symbol':symbol,
			'asset':f"{symbol}-USDT",
			'asset_amount':0,
			'profit':'',
			'status':'open',
			'cash':cash,
			'cash_per_purchase':cash_per_purchase,
			'avgprice':0,
			'amount_invested':0,
			'txns':[],
		}
		txn = self.purchase(symbol,cash_per_purchase)
		trade['txns'].append(txn)
		trade['cash'] -= cash_per_purchase
		trade['amount_invested'] += cash_per_purchase
		trade['asset_amount'] += txn['assets']
		trade['avgprice'] = trade['amount_invested']/trade['asset_amount']

		self.client.trades.insert_one(trade)

	def update_trade(self,config):
		trade = self.client.trades.find_one({"_id":tradeid})
		asset = self.get_asset(trade['symbol'])
		bestAsk,bestBid = exchange_api.get_price(asset['symbol'])
		config = {
			'last_bid':bestBid,
			'last_ask':bestAsk,
			'last_updated':datetime.now()
		}

		self.client.bots.update_one({"_id":tradeid},{"$set":config})

	def add_txn(self,tradeid,txn):
		trade = self.client.trades.find_one({"tradeid":tradeid})
		txns = trade['txns']
		txns.append(txn)
		self.update_trade({"tradeid":trade['tradeid'],"txns":txns})

	def purchase(self,symbol,cash):
		bestAsk = get_best_ask
		transaction = {
			orderid:oid,
			type:'purchase',
			assets:cash/bestAsk,
			cash:cash
		}
		return transaction

	def sale(self,symbol,assets):
		bestBid = get_best_bid
		transaction = {
			orderid:oid,
			type:'sale',
			assets:assets,
			cash:bestBid * assets
		}
		return transaction

	def update_asset(self,config):
		asset = config['asset']
		config['last_updated'] = datetime.now()
		self.client.assets.update_one({'asset':asset},{"$set":config},upsert=True)
