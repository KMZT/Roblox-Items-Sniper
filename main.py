import requests, json, time, threading, random
from urllib3.exceptions import InsecureRequestWarning
from colorama import Fore, init

init()

# Load configuration settings from settings.json
settings = json.load(open("settings.json", "r"))
item_ids = settings["items"]  # Extract item IDs and prices
cookies = settings["cookie"]
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

# Create separate sessions for each account
sessions = []
for cookie in cookies:
    session = requests.Session()
    session.cookies['.ROBLOSECURITY'] = cookie
    sessions.append(session)

token = [None] * len(sessions)
payload = [{"itemType": "Asset", "id": id} for id in item_ids]
cache = []
checks = 0

start_time = time.time()

# Create a dictionary to track items that have been warned and bought
item_warnings = {}

def refresh_tokens(index):
    while True:
        _set_auth(index)
        time.sleep(150)

def _set_auth(index):
    global token
    try:
        conn = sessions[index].post("https://auth.roblox.com/v2/logout")
        if conn.headers.get("x-csrf-token"):
            token[index] = conn.headers["x-csrf-token"]
    except:
        time.sleep(5)
        return _set_auth(index)

def get_product_id(id, index):
    try:
        conn = sessions[index].get(f"https://economy.roblox.com/v2/assets/{id}/details", verify=False)
        data = conn.json()

        if conn.status_code == 200:
            return {
                "id": data["ProductId"],
                "creator": data["Creator"]["Id"]
            }
        else:
            time.sleep(1)
            return get_product_id(id, index)
    except:
        time.sleep(1)
        return get_product_id(id, index)

def buy_item(product_id, seller_id, price, index):
    try:
        body = {
            "expectedCurrency": 1,
            "expectedPrice": price,
            "expectedSellerId": seller_id
        }
        headers = {
            "x-csrf-token": token[index],
        }
        conn = sessions[index].post(f"https://economy.roblox.com/v1/purchases/products/{product_id}", headers=headers, json=body)
        if conn.status_code == 200:
            print(f"Account {index + 1}: Bought item {product_id}")
    except Exception as error:
        print(f"Error on account {index + 1}: {error}")
        pass  # Ignore errors, do not retry buying

def watcher():
    global token, sessions, checks
    while True:
        try:
            index = random.randint(0, len(sessions) - 1)  # Randomly choose an account
            headers = {
                "x-csrf-token": token[index],
                "cache-control": "no-cache",
                "pragma": "no-cache",
            }
            conn = sessions[index].post("https://catalog.roblox.com/v1/catalog/items/details", json={"items": payload}, headers=headers, verify=False)

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
                                    r_data = get_product_id(item_id, index)
                                    price = item["price"]
                                    buy_item(r_data["id"], r_data["creator"], price, index)
            elif conn.status_code == 403:
                _set_auth(index)
        except Exception as error:
            pass
        time.sleep(settings["watch_speed"])

if __name__ == '__main__':
    # Start token refresh threads for each account
    for i in range(len(sessions)):
        threading.Thread(target=refresh_tokens, args=(i,)).start()
        
    # Wait until all tokens are set
    while any(t is None for t in token):
        time.sleep(1)

    threading.Thread(target=watcher).start()
