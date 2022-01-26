from time import sleep
from re import compile, match
from collections import namedtuple
from random import choice, randint

import requests
from bs4 import BeautifulSoup as bs
import undetected_chromedriver as uc


# Lizard object in namedtuples.
Lizard = namedtuple('Lizard', ['id_', 'opensea', 'collection', 'price', 'currency', 'raritycow', 'rank', 'img'])

# Stack all regex.
Regex = namedtuple('Regex', ['id', 'price'])
id_reg = compile("^/assets/[a-zA-Z0-9]+/([0-9]+)$")
price_reg = compile("([0-9]+(?:\.[0-9]+)?)")
regex = Regex(id_reg, price_reg)

# Stack all urls.
SourceLink = namedtuple('SourceLink', ['opensea', 'raritycow'])
raritycow_sourcelink = "http://raritycow.io/token/metalizards-official/"
opensea_sourcelink = "https://opensea.io/collection/metalizards-official?search[sortBy]=LISTING_DATE&search[sortAscending]=false"
sourcelink = SourceLink(opensea_sourcelink, raritycow_sourcelink)


resolution = [
    "1024,768",
    "1152,864",
    "1366,768",
    "1280,720",
    "1280,1024",
    "1440,900",
    "1400,1050",
    "1600,1024",
    "1600,1200",
    "1680,1050",
    "1920,1080",
    "1920,1200",
    "2048,1536",
    "2560,1440",
    "2560,1600"
    ]

def start_scrape():
    # Init chromedriver.
    options = uc.ChromeOptions()
    reso = f"--no-first-run --no-service-autorun --window-size={choice(resolution)}"
    options.add_argument(reso)  # Change resolution for each time to be less detectable.
    driver = uc.Chrome(options=options)
    # Start scrapping.
    driver.get(sourcelink.opensea)
    sleep(randint(11, 27))
    soup = bs(driver.page_source,"lxml")
    driver.quit()

    def get_rank(id: str) -> str:
        """Scrape site raritycow to get rarity rank"""
        url = sourcelink.raritycow + id
        requete = requests.get(url)
        page = requete.content
        soup = bs(page, 'lxml')
        rank = soup.find("span", {"id": "t_rank"}).string
        img = soup.find("img", {"id": "t_img"}).get('src')
        return rank, url, img

    # List of finded lizards.
    lizard_manager = {}

    # Get all of offers cards.
    main_div = soup.find_all("article", {"class": "Assetreact__AssetCard-sc-bnjqwy-2 fXFHnS Asset--loaded AssetSearchList--asset"})
    # Itere on cards.
    for i,elt in enumerate(main_div):
        # Create a new lizard.
        lizard_manager[i]={'collection': "MetaLizards Official"}

        # Add Lizard's Opensea link.
        opensea_link = elt.find("a").get('href', "")
        lizard_manager[i]['opensea'] = "https://opensea.io" + opensea_link

        # Add lizard id.
        id_os = match(regex.id, opensea_link).group(1)
        lizard_manager[i]['id_'] = id_os

        # Scope on sells infos.
        info_div = elt.find("div", {"class": "Blockreact__Block-sc-1xf18x6-0 Flexreact__Flex-sc-1twd32i-0 SpaceBetweenreact__SpaceBetween-sc-jjxyhg-0 lcXrbo jYqxGr gJwgfT"})
        sell_div = info_div.find("div", {"class": "Pricereact__DivContainer-sc-t54vn5-0 iBLrYW Price--main AssetCardFooter--price-amount"})
        if sell_div == None: # It sometimes happens that a lizard is listed without having a price.
            print(f"error with {id_os} to {opensea_link}")
            del lizard_manager[i]
            continue

        # Add price.
        price = sell_div.find(text=regex.price)
        lizard_manager[i]['price'] = price.strip()

        # Add currency.
        currency_div = sell_div.find("div", {"class": "Blockreact__Block-sc-1xf18x6-0 Flexreact__Flex-sc-1twd32i-0 FlexColumnreact__FlexColumn-sc-1wwz3hp-0 VerticalAlignedreact__VerticalAligned-sc-b4hiel-0 CenterAlignedreact__CenterAligned-sc-cjf6mn-0 Avatarreact__AvatarContainer-sc-sbw25j-0 hkQgWj jYqxGr ksFzlZ iXcsEj cgnEmv dukFGY"})
        img_currency = currency_div.find('span')
        if (img_currency == None) or 'Price--eth-icon' in img_currency.get('class', "Price--eth-icon"): # It avoids crashes and puts 'ETH' by default.
            currency = "ETH"
        else:
            currency = "WETH"
        lizard_manager[i]['currency'] = currency

        # Add rarity rank, image link and raritycow url.
        rank, url, img = get_rank(id_os)
        lizard_manager[i]['rank'] = rank
        lizard_manager[i]['img'] = img
        lizard_manager[i]['raritycow'] = url

    inlist = []
    for l in lizard_manager:
        inlist.append(Lizard(**lizard_manager[l]))

    return inlist

if __name__ == '__main__': # For test
    opensea_sourcelink = "https://opensea.io/collection/metalizards-official?search[sortAscending]=true&search[sortBy]=PRICE"
    sourcelink = SourceLink(opensea_sourcelink, raritycow_sourcelink)
    from pprint import pprint
    u = start_scrape()
    pprint(u)