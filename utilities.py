import time, requests
import pandas as pd
from datetime import datetime

def try_request(url,method='get',headers={'User-Agent': 'Mozilla/5.0'}):
	status = 0
	attempts = 0
	while status != 200:
		try:
			response = requests.request(method,url,headers=headers)
			status = response.status_code
			attempts += 1
			if attempts % 10 == 0:
				if status != 200:
					print(f"Error {response.status_code}! {url}")
				time.sleep(5)
		except Exception as e:
			print(e)
			print(f"Time: {datetime.now()}\n")
		if attempts > 5:
			print(f"Error getting response from {url}")
			return {'data':None}
	return response

def init_df(suffix=''):
	cols = ['timestamp','date',f'open{suffix}',f'high{suffix}',f'low{suffix}',f'close{suffix}',f'volume{suffix}']
	return pd.DataFrame(columns=cols)
