import json
from os import path
from math import ceil
from time import sleep
from collections import namedtuple
from configparser import ConfigParser

import requests
from pyrogram import Client
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from scraper.scraper import start_scrape

# read config.ini.
config = ConfigParser()
config.read('config.ini')

# stock conversion rates.
ETH = namedtuple('ETH', ["USD", "EUR"])
WETH = namedtuple('WETH', ["USD", "EUR"])

# Get config.ini.
CRYPTOCOMPARE_TOKEN = config['cryptocompare']['TOKEN']
CHANNEL = config['telegram']['channel']


class Main(Client):
    def __init__(self):
        # Load list of lizards offers already send.
        self.already_send = self.load_sending()  # Juste a string with id and price.
        # Get actual price of Ethereum and Wethereum.
        currencies = self.get_currencies()
        self.Eth = ETH(**currencies['ETH'])  # To a namedtuple.
        self.Weth = WETH(**currencies['WETH'])
        # Init pyrogram client
        super().__init__("metalizards_bot")
        self.init_schedulers()
        self.run()  # Pyrogram main loop.

    async def job(self):
        """ Main function who call scraper and itere, format message and send to channel. """
        scrape_result = start_scrape()
        for lizard in scrape_result:
            # Signature composed by id lizard and price. 
            await self.save_lizard(lizard)
            signature = f"L{lizard.id_}#{lizard.price}"
            if signature in self.already_send:  # Skip this lezard if already send in telegram.
                continue
            formated_text = await self.format_message(lizard)
            await self.send_message(CHANNEL , text=formated_text, protect_content=True, parse_mode='html')
            self.already_send += signature  # Add this signature in "already_send".
            sleep(4)  # To avoid flood pyrogram protection.

    async def save_lizard(self, lizard):
        """ Save lezard with all infos if has never saved before. """
        data = lizard._asdict()  # Namedtuples aren't json compatible.
        with open('data.json', 'r', encoding='utf-8') as fr:
            saved_lizards = json.loads(fr.read())
        if data not in saved_lizards:
            new_save = saved_lizards[:]  # Need copy avoids circular reference error.
            with open('data.json', 'w', encoding='utf-8') as fw:
                new_save.append(data)
                json.dump(new_save, fw, ensure_ascii=False, indent=4)

    async def save_sending(self):
        """ Make a save.txt with all lizard offers inside. """
        with open("save.txt", 'w') as f:
            f.write(self.already_send)
    
    def load_sending(self) -> str:
        """ Read the save.txt with all lizard offers inside. """
        already_send = ""  # If path not exist.
        if path.exists("save.txt"):
            with open("save.txt", "r") as f:
                already_send = f.read()
        return already_send

    async def format_message(self, lizard) -> str:
        """ Compose message with important lizard's info with html parse_mod. """
        # Compute conversion devise in usd and eur.
        if lizard.currency == 'ETH':
            conv = f"{ceil(float(lizard.price) * float(self.Eth.USD))}$ or {ceil(float(lizard.price) * float(self.Eth.EUR))}€"
        else:
            conv = f"{ceil(float(lizard.price) * float(self.Weth.USD))}$ or {ceil(float(lizard.price) * float(self.Weth.EUR))}€"
        # Compose message body.
        id_price_devise = f"Lizard <b>#{lizard.id_}</b> @ ⟠{lizard.price} <b>{lizard.currency}</b> ({conv})\n"
        rank = f"Rank:  <b>{lizard.rank}</b>\n\n"
        links = f"<a href={lizard.opensea}>OpenSea</a>\n<a href={lizard.raritycow}>RarityCow</a>"
        return id_price_devise + rank + links
    
    def get_currencies(self) -> dict:
        """
        Request CryptoCompare API to get price:
            -ETH / USD,EUR
            -WETH / USD,EUR
        """
        r = requests.get(f"https://min-api.cryptocompare.com/data/pricemulti?fsyms=ETH,WETH&tsyms=USD,EUR&api_key={CRYPTOCOMPARE_TOKEN}")
        in_dict = eval(r.text)
        return in_dict

    def init_schedulers(self):
        """Periodic tasks."""
        scheduler = AsyncIOScheduler()
        # Job function is main function to scrape Opensea and send message.
        scheduler.add_job(self.job, "interval", seconds=60)
        # Automatique save.
        scheduler.add_job(self.save_sending, "interval", seconds=600)
        # Update currency price.
        scheduler.add_job(self.get_currencies, "interval", seconds=1800)
        scheduler.start()
        

if __name__ == '__main__':
    APP = Main()
