from httpx import AsyncClient
from bs4 import BeautifulSoup
from .types import Result
import asyncio
import logging
import re


logger = logging.getLogger(__name__)


class AvitoScrapingException(Exception):
    pass


class TooManyRequests(AvitoScrapingException):
    pass


class ClosedAd(AvitoScrapingException):
    pass


async def scrape_content(content: str) -> dict:
    # data-marker = item-view/closed-warnin
    area_pattern = r'(\d+(?:[.,]\d+)?)\s*м²'
    rooms_pattern = r'(\d+)\s*-\s*к\.'
    floor_pattern = r'(\d+)\s*/\s*(\d+)\s*эт\.'

    soup = BeautifulSoup(content, 'html.parser')

    if soup.find('a', {'data-marker': 'item-view/closed-warning'}):
        raise ClosedAd()

    title = soup.find('h1', itemprop='name').text

    room_area = re.search(area_pattern, title).group(1)
    room_area = float(room_area.replace(',', '.'))

    number_of_rooms_in_flat = re.search(rooms_pattern, title).group(1)
    number_of_rooms_in_flat = int(number_of_rooms_in_flat)

    flour, flours_in_building = re.search(floor_pattern, title).groups()
    flour = int(flour)
    flours_in_building = int(flours_in_building)

    price = soup.find('span', itemprop='price').text
    price = int(re.sub(r'\D', '', price))

    address = soup.find('div', itemprop='address').find('span').text

    description = soup.find('div', itemprop='description')
    description_text = ''
    for el in description.find_all('p'):
        description_text += el.text.replace('<br/>', '\n') + '\n'

    return {
        'price': price,
        'room_area': room_area,
        'number_of_rooms_in_flat': number_of_rooms_in_flat,
        'flour': flour,
        'flours_in_building': flours_in_building,
        'address': address,
        'description': description_text,
    }


async def make_requests(urls: list[str]) -> list[str]:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/58.0.3029.110 Safari/537.3'
    }

    results = []

    async with AsyncClient() as client:
        for url in urls:
            response = await client.get(url, headers=headers)

            if response.status_code == 200:
                logger.info(f"Successfully fetched {url}")
                results.append(response.text)
            else:
                logger.error(f"Error {response.status_code} while fetching {url}\n"
                             f"Response: {response.text}")

    return results


async def scrape_avito_room_ad(url: str) -> Result | None:

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
        'Referer': 'https://web.telegram.org/',
        'Accept-Language': 'da, en-gb, en',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept': 'text / html, application / xhtml + xml, application / xml; '
        'q = 0.9, image / avif, image / webp, * / *;q = 0.8'

    }

    async with AsyncClient() as client:
        response = await client.get(url, headers=headers, follow_redirects=True)

        if response.status_code == 200:
            logger.info(f"Successfully fetched {url}")
            ad = await scrape_content(response.text)
            result = Result(
                url=url,
                **ad
            )
            return result
        elif response.status_code == 429:
            text = f"Too many requests. Avito blocks request to {url}"
            logger.error(text)
            raise TooManyRequests(text)
        else:
            text = (f"Error {response.status_code} while fetching {url}\n"
                    f"Response: {response.text}")
            logger.error(text)
            raise AvitoScrapingException(text)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(scrape_avito_room_ad('https://www.avito.ru/sankt-peterburg/komnaty/komnata_26m_v_4-k._25et._3179086012'))
