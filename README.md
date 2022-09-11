# A simple class for asynchronously accessing data from Pixiv   
This module includes a simple class for accessing information and image data from [Pixiv](https://www.pixiv.net/) by the cookies you provided. 

To use this module, you need to have `httpx` installed. The easiest way is to install it through pip:
```bash
pip install httpx
```

Here is an example for using this module:
``` py
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
            *(pixu.download_artwork(artwork_id, f'./downloads/{artwork_id}.jpg') \
            for artwork_id in artwork_ids)
        )
    except Exception as e:
        msg = e if len(str(e)) else type(e)
        print(f'Exception occured: {msg}, download failed.')
        return 
        
asyncio.run(test_download_from_user())
```

`config.json` may look like this: 
```json
{
    "cookie": "your_cookies", 
    "proxies": {
        "http://": "http://127.0.0.1:1234", 
        "https://": "http://127.0.0.1:1234"
    }
}
```

This piece of code is also in `pixu.py`. 

# robots.txt
From my understanding, the methods of `Pixu` class are not violating the current [robots.txt](https://www.pixiv.net/robots.txt) so far. Please contact me if related issues exist. 