# Positive EV Sports Betting Algorithm

## Description

This repository contains a positive Expected Value (EV) sports betting algorithm designed to scrape betting odds and make informed decisions based on historical data. The algorithm uses various Python libraries to extract, process, and notify users about potential bets.

## Repository Contents

1. **betting-algo-2.0.py**:
   - A web scraper that uses the Selenium library to extract betting odds.
   - Utilizes the Twilio API for notifications.
   - Data manipulation with the Pandas library.
   - Betting odds processing with the pybettor library.

2. **betting spreadsheet.xlsx**:
   - A comprehensive record of bets placed, their outcomes, and associated statistics.
   - Fields include: Date, Event Name, Market Name, Bet Name, Odds, CLV, Stake, Potential Payout, Result, Net Profit, Rolling Net Profit, and Overall Net Profit.

## Installation & Setup

1. **Prerequisites**:
   - Python 3.x
   - Chrome WebDriver for Selenium

2. **Python Libraries**:
   - Install the required libraries using pip:
     ```bash
     pip install selenium pandas twilio pybettor
     ```

3. **Setup**:
   - Ensure you have set up the Twilio API credentials if you wish to receive notifications.
   - Update the Chrome WebDriver path in the script if it's not in your system's PATH.

## Usage

1. Run the Python script to start the web scraper:
   ```bash
   python betting-algo-2.0.py
