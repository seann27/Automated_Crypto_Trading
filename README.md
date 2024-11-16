# Automated Crypto Trading

## Overview
This project uses krakenex to retrieve candlestick data and to buy/sell cryptocurrencies. The project operates through two scripts that should be run concurrently.

## Prerequisites
- Kraken API keys
- MongoDB instance
- Automated telegram account configured with the telegram_send Python library

## Required Python Libraries
- pandas
- numpy
- pymongo
- krakenex
- telegram_send

## Project Structure

### database/update_indicators.py
This script interfaces with the Kraken API to fetch candlestick data and calculates custom indicators using the `UpsideMomentum.py` indicator module. The calculated indicator values are then stored in a NoSQL MongoDB database.

### trading/swodl.py
This script handles the automated trading functionality:
- Scans MongoDB database for cryptocurrencies meeting buy requirements
- Monitors existing trades for sell signal conditions
- Executes buy/sell transactions when conditions are met
- Updates MongoDB with transaction details
- Sends real-time notifications via Telegram for all transactions

### UpsideMomentum.py
Custom indicator module for technical analysis calculations.

## Installation & Setup
1. Clone this repository
2. Install required Python packages:
```bash
pip install pandas numpy pymongo krakenex telegram_send
```
3. Configure your Kraken API keys
4. Set up your MongoDB instance
5. Configure telegram_send with your bot credentials

## Running the Application
Run both scripts concurrently:
1. Start the indicator update script:
```bash
python database/update_indicators.py
```
2. Start the trading script:
```bash
python swodl.py
```

The system will then:
- Continuously update indicators in the database
- Monitor for trading signals
- Execute trades automatically
- Send Telegram notifications for all transactions

## Security Note
Ensure your API keys and sensitive credentials are properly secured and never committed to the repository.

## License
MIT License

Copyright (c) 2024

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.
