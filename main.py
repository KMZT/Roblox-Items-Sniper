import requests, json, time, threading, random, os
from urllib3.exceptions import InsecureRequestWarning
from colorama import Fore, Back, Style, init

init()

# Load configuration settings from settings.json
settings = json.load(open("settings.json", "r"))
item_ids = settings["items"]  # Extract item IDs and prices
cookie = settings["cookies"]
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

session = requests.session()
for s in cookie:
    session.cookies['.ROBLOSECURITY'] = s

token = None
payload = [{ "itemType": "Asset", "id": id } for id in item_ids]
cache = []

logs = []
checks = 0

start_time = time.time()

# Create a dictionary to track items that have been warned and bought
item_warnings = {}

def refresh_tokens():
    while True:
        _set_auth()
        time.sleep(150)

def _set_auth():
    global token, session
    try:
        conn = session.post("https://auth.roblox.com/v2/logout")
        if conn.headers.get("x-csrf-token"):
            token = conn.headers["x-csrf-token"]
    except:
        time.sleep(5)
        return _set_auth()

def get_product_id(id):
    try:
        conn = session.get(f"https://economy.roblox.com/v2/assets/{id}/details", verify=False)
        data = conn.json()

        if conn.status_code == 200:
            return {
                "id": data["ProductId"],
                "creator": data["Creator"]["Id"]
            }
        else:
            time.sleep(1)
            return get_product_id(id)
    except:
        time.sleep(1)
        return get_product_id(id)

def buy_item(product_id, seller_id, price):
    global logs

    try:
        body = {
            "expectedCurrency": 1,
            "expectedPrice": price,
            "expectedSellerId": seller_id
        }
        headers = {
            "x-csrf-token": token,
        }
        conn = session.post(f"https://economy.roblox.com/v1/purchases/products/{product_id}", headers=headers, json=body)
        data = conn.json()
        if conn.status_code == 200:
            print("Bought")
        else:
            print(data)
        # Purchase happens only once, so no retry logic is needed
    except:
        pass  # Ignore errors, do not retry buying

def watcher():
    global token, session, checks, logs
    while True:
        try:
            headers = {
                "x-csrf-token": token,
                "cache-control": "no-cache",
                "pragma": "no-cache",
            }
            conn = session.post("https://catalog.roblox.com/v1/catalog/items/details", json={ "items": payload }, headers=headers, verify=False)

            data = conn.json()
            if conn.status_code == 200:
                checks += 1
                if "data" in data:
                    for item in data["data"]:
                        item_id = item['id']
                        item_name = item['name']

                        if "price" in item and not item_id in cache:
                            purchase_price = item_ids.get(str(item_id))
                            if purchase_price is not None:
                                if item["price"] <= purchase_price:
                                    
                                    cache.append(item_id)
                                    r_data = get_product_id(item_id)
                                    price = item["price"]
                                    buy_item(r_data["id"], r_data["creator"], price)
            elif conn.status_code == 403:
                _set_auth()
        except Exception as error:
            pass
        time.sleep(settings["watch_speed"])

if __name__ == '__main__':
    threading.Thread(target=refresh_tokens).start()
    while token == None:
        time.sleep(1)
    threading.Thread(target=watcher).start()
