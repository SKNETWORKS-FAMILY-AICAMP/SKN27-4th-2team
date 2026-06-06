import json

from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import os
from dotenv import load_dotenv

load_dotenv()
DOG_API_KEY = os.getenv("THE_DOG_API_KEY")

def request_json(path, api_key=DOG_API_KEY, params=None):
    query = f"?{urlencode(params)}" if params else ""
    url = f"https://api.thedogapi.com/v1/{path}/{query}"

    request = Request(url, headers={"x-api-key": api_key})
    try:
        with urlopen(request, timeout=10) as response:
            body = response.read().decode('utf-8')
            return json.loads(body)
    except HTTPError as e:
        detail = e.read().decode('utf-8', errors='replace')
        raise RuntimeError(f"TheDogAPI request failed: HTTP {e.code} {detail}") from e
    except URLError as e:
        raise RuntimeError(f"TheDogAPI request failed: {e.reason}") from e

# def main():
#     total_breeds = request_json("breeds")
#     print(f"Total breeds: {len(total_breeds)}")