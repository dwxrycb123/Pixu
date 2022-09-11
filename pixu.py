import re 
from typing import Optional, List
from datetime import datetime
import httpx 
import json
import asyncio
import os
from io import BytesIO
from functools import wraps

settings = {
    "default_headers" : {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
            AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 \
            Safari/537.36", 
        "Referer": "https://www.pixiv.net/"
    }, 
    "retries": 3
}

def retries(retries: int = 1):
    def decorate(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for iter in range(retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    msg_e = e if len(str(e)) else type(e)
                    msg = f'Exception occurred: {msg_e}, ''{iter + 1}-th retrying...'
                    if (iter < retries - 1):
                        msg += '{iter + 1}-th retrying...'
                    else:
                        msg += f'failed after {retries} retry attempts...'
                    print(msg)
                    return 
        return wrapper
    return decorate

class Pixu:
    """
    An utility class for accessing pixiv site by your cookies
    """
    user_link_pattern = re.compile(r'<a href="/users/(?P<user_id>\d+)"')
    search_user_url = "https://www.pixiv.net/search_user.php"
    user_artworks_url = lambda user_id: \
        f"https://www.pixiv.net/ajax/user/{user_id}/profile/all?lang=zh"
    artwork_info_url = lambda user_id, artwork_id: \
        f"https://www.pixiv.net/ajax/user/{user_id}/illusts?ids%5B%5D={artwork_id}&lang=zh"
    update_date_re = (r'(?P<year>\d+)-(?P<month>\d+)-(?P<day>\d+)T'
        '(?P<hour>\d+):(?P<minute>\d+):(?P<second>\d+)\+09:00')
    update_date_pattern  = re.compile(update_date_re)

    def __init__(self, cookie: str, proxies: Optional[dict] = None, \
        headers: Optional[dict] = None, retries: int = 0) -> None:
        self.headers = headers if headers else settings["default_headers"]
        self.headers.update({'Cookie': cookie})
        self.proxies = proxies 
        self.get_args = {
            'headers': self.headers
        }
        self.client_args = {
            'proxies': proxies, 
        }
        Pixu.retries = retries

    @retries(settings["retries"])
    async def search_user(self, name: str) -> List[int]:
        remove_repeat = lambda x: list(set(x))
        params = {
            "nick": name, 
            "s_mode": "s_usr"
        }
        async with httpx.AsyncClient(**self.client_args, params=params) as client:
            r = await client.get(self.search_user_url, **self.get_args)
            return remove_repeat(self.user_link_pattern.findall(repr(r.text)))

    @retries(settings["retries"])
    async def get_artworks_from_user(self, user_id: int) \
        -> List[int]:
        async with httpx.AsyncClient(**self.client_args) as client:
            r = await client.get(Pixu.user_artworks_url(user_id), **self.get_args)
            r_json: dict = r.json() 
            artworks = r_json["body"]["illusts"].keys()
            return artworks

    @retries(settings["retries"])
    async def get_artwork_info(self, user_id:int, artwork_id: int) -> dict:
        async with httpx.AsyncClient(**self.client_args) as client:
            r = await client.get(Pixu.artwork_info_url(user_id, artwork_id), **self.get_args)
            r_json: dict = r.json()
            artwork_info = {"raw": r_json["body"][str(artwork_id)]}
            raw_update_date = artwork_info["raw"]["updateDate"]
            d = self.update_date_pattern.match(raw_update_date).groupdict()
            update_date = datetime(**{k: int(v) for k, v in d.items()})
            artwork_info['update_date'] = update_date
            artwork_info['url'] = (f"https://i.pximg.net/img-original/img/{d['year']}/"
                f"{d['month']}/{d['day']}/{d['hour']}/{d['minute']}/{d['second']}/"
                f"{artwork_id}_p0.jpg")
            return artwork_info
    
    @retries(settings["retries"])
    async def download_image(self, image_url: str, save_path: str) -> None:
        dirname = os.path.dirname(save_path)
        if not os.path.exists(dirname):
            os.makedirs(dirname)        

        with httpx.stream("GET", image_url, **self.client_args, **self.get_args) as r:
            with open(save_path, 'wb') as f:
                for data in r.iter_bytes():
                    f.write(data)
    
    async def download_artwork(self, user_id: int, artwork_id: int, save_path: str) -> None:
        artwork_info = await self.get_artwork_info(user_id, artwork_id)   
        url = artwork_info['url']
        await self.download_image(url, save_path)

if __name__ == '__main__':
    # a simple test 
    with open('./config.json', 'r') as f:
        config = json.load(f)
    pixu = Pixu(**config)

    async def test_download_from_user(name='千種みのり'):
        try:        
            user_ids = await pixu.search_user(name)
            print(f'user_ids: {user_ids}')
            if not user_ids:
                print('get user_id failed.')
                return 
            
            user_id = user_ids[0]
            artwork_ids = await pixu.get_artworks_from_user(user_id)
            print(f'artwork_ids: {artwork_ids}')
            if not artwork_ids:
                print('get artwork_ids failed.')
                return 
            artwork_ids = list(artwork_ids)[:5]

            await asyncio.gather(
                *(pixu.download_artwork(user_id, artwork_id, f'./downloads/{artwork_id}.jpg') \
                for artwork_id in artwork_ids)
            )
        except Exception as e:
            msg = e if len(str(e)) else type(e)
            print(f'Exception occured: {msg}, download failed.')
            return 
    
    asyncio.run(test_download_from_user())