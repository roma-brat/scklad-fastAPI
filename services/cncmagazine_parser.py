import requests
from bs4 import BeautifulSoup
import re
import json
import urllib.parse


class CNCmagazineParser:
    def __init__(self):
        self.base_url = "https://cncmagazine.ru"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
    
    def get_product_info(self, url: str) -> dict:
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            product_data = {
                'name': self._get_name(soup),
                'article': self._get_article(soup, url),
                'price': self._get_price(soup),
                'image_url': self._get_image(soup),
                'specifications': self._get_specifications(soup, url),
                'description': self._get_description(soup),
            }
            
            return product_data
            
        except requests.exceptions.RequestException as e:
            return {'error': str(e)}
    
    def _get_name(self, soup: BeautifulSoup) -> str:
        h1 = soup.find('h1', class_='ty-product-block-title')
        if h1:
            name = h1.get_text(strip=True)
            return name.split('купить')[0].strip()
        
        h1 = soup.find('h1')
        if h1:
            return h1.get_text(strip=True)
        
        title = soup.find('title')
        if title:
            return title.get_text(strip=True).split('|')[0].split('―')[0].strip()
        
        return ''
    
    def _get_article(self, soup: BeautifulSoup, url: str) -> str:
        # Try to get from SKU element
        sku = soup.find('div', class_='cnc-product-detail__sku')
        if sku:
            text = sku.get_text(strip=True)
            match = re.search(r'(\d+)', text)
            if match:
                return match.group(1)
        
        # Try to get from product code in quick info
        quick_info = soup.find('div', class_='cnc-product-detail__qucik-info-left')
        if quick_info:
            text = quick_info.get_text(strip=True)
            match = re.search(r'(\d+)', text)
            if match:
                return match.group(1)
        
        # Extract from URL pattern
        path = urllib.parse.urlparse(url).path
        match = re.search(r'/([a-z0-9\-]+)/?$', path, re.IGNORECASE)
        if match:
            return match.group(1).upper()
        
        return ''
    
    def _get_price(self, soup: BeautifulSoup) -> str:
        price_block = soup.find('span', class_='ty-price-num')
        if price_block:
            return price_block.get_text(strip=True)
        
        price_block = soup.find('div', class_='cnc-product-detail__price-actual')
        if price_block:
            text = price_block.get_text(strip=True)
            match = re.search(r'([\d\s]+)', text)
            if match:
                return match.group(1).strip()
        
        return ''
    
    def _get_image(self, soup: BeautifulSoup) -> str:
        img = soup.find('a', class_='ty-previewer')
        if img and img.get('href'):
            return img.get('href')
        
        img = soup.find('img', id=re.compile(r'preview'))
        if img and img.get('src'):
            return img.get('src')
        
        return ''
    
    def _get_specifications(self, soup: BeautifulSoup, url: str) -> dict:
        specs = {}
        
        # Extract article code from URL for tool-specific specs
        path = urllib.parse.urlparse(url).path
        article_match = re.search(r'([a-z]\d+[qt]-sducr\d*)', path, re.IGNORECASE)
        if article_match:
            article = article_match.group(1).upper()
            specs['article_code'] = article
            
            # Parse tool dimensions from article code
            # Example: A16Q-SDUCR07 -> diameter=16mm, plate size=07
            size_match = re.search(r'[A-Z]?(\d+)[QT]', article)
            if size_match:
                specs['diameter'] = f"{size_match.group(1)} мм"
        
        # Try to find specs in text
        text = soup.get_text()
        
        # Find "Технические характеристики" section
        if 'Технические характеристики' in text:
            lines = text.split('\n')
            in_specs = False
            for i, line in enumerate(lines):
                if 'Технические характеристики' in line:
                    in_specs = True
                    continue
                if in_specs and line.strip():
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip()
                        if key and value and len(key) < 30:
                            specs[key] = value
                    elif len(line.strip()) > 30:
                        break
        
        # Look for common specs in the page
        spec_patterns = [
            (r'мин[.\s]*диаметр[^\d]*(\d+)', 'Мин. диаметр обработки'),
            (r'длина[^\d]*(\d+)', 'Длина'),
            (r'Угол[^\d]*(\d+)', 'Угол в плане'),
            (r'Исполнение[:\s]*(\w+)', 'Исполнение'),
            (r'Правое|Левое', 'Тип'),
        ]
        
        for pattern, name in spec_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match and name not in specs:
                value = match.group(1) if match.lastindex else match.group()
                if value.lower() in ['правое', 'левое']:
                    value = value.capitalize()
                specs[name] = f"{value} мм" if 'мм' in pattern else value
        
        return specs
    
    def _get_description(self, soup: BeautifulSoup) -> str:
        desc_block = soup.find('div', class_='ty-product-full-description')
        if desc_block:
            text = desc_block.get_text(strip=True)
            if len(text) > 50:
                return text[:2000]
        
        return ''


def parse_cncmagazine(url: str) -> dict:
    parser = CNCmagazineParser()
    return parser.get_product_info(url)


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = 'https://cncmagazine.ru/rezcy-so-smennymi-plastinami/rastochnye-opravki/a16q-sducr07-derzhavka-rastochnaya/'
    
    result = parse_cncmagazine(url)
    print(json.dumps(result, ensure_ascii=False, indent=2))
