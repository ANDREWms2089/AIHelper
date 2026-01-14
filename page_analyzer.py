from playwright.async_api import Page
from bs4 import BeautifulSoup
import re


class PageAnalyzer:
    def __init__(self, page: Page):
        self.page = page
    
    async def get_page_summary(self) -> dict:
        html = await self.page.content()
        soup = BeautifulSoup(html, 'lxml')
        for script in soup(["script", "style", "noscript"]):
            script.decompose()
        
        summary = {
            'url': self.page.url,
            'title': await self.page.title(),
            'headings': self._extract_headings(soup),
            'links': self._extract_links(soup),
            'buttons': self._extract_buttons(soup),
            'forms': self._extract_forms(soup),
            'text_content': self._extract_main_text(soup),
            'interactive_elements': self._extract_interactive_elements(soup)
        }
        
        return summary
    
    def _extract_headings(self, soup: BeautifulSoup) -> list:
        headings = []
        for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            for heading in soup.find_all(tag):
                text = heading.get_text(strip=True)
                if text:
                    headings.append({'level': tag, 'text': text})
        return headings[:10]
    
    def _extract_links(self, soup: BeautifulSoup) -> list:
        links = []
        for link in soup.find_all('a', href=True):
            text = link.get_text(strip=True)
            href = link.get('href', '')
            if text or href:
                links.append({
                    'text': text[:100],
                    'href': href,
                    'visible': bool(text)
                })
        return links[:30]
    
    def _extract_buttons(self, soup: BeautifulSoup) -> list:
        buttons = []
        for btn in soup.find_all(['button', 'input[type="button"]', 'input[type="submit"]']):
            text = btn.get_text(strip=True) or btn.get('value', '') or btn.get('aria-label', '')
            if text:
                buttons.append({
                    'text': text[:100],
                    'type': btn.name,
                    'id': btn.get('id', ''),
                    'class': ' '.join(btn.get('class', []))
                })
        for btn in soup.find_all(attrs={'role': 'button'}):
            text = btn.get_text(strip=True) or btn.get('aria-label', '')
            if text and text not in [b['text'] for b in buttons]:
                buttons.append({
                    'text': text[:100],
                    'type': 'div/span with role=button',
                    'id': btn.get('id', ''),
                    'class': ' '.join(btn.get('class', []))
                })
        
        return buttons[:20]
    
    def _extract_forms(self, soup: BeautifulSoup) -> list:
        forms = []
        for form in soup.find_all('form'):
            form_info = {
                'action': form.get('action', ''),
                'method': form.get('method', 'GET'),
                'inputs': []
            }
            
            for input_elem in form.find_all(['input', 'textarea', 'select']):
                input_info = {
                    'type': input_elem.get('type', input_elem.name),
                    'name': input_elem.get('name', ''),
                    'id': input_elem.get('id', ''),
                    'placeholder': input_elem.get('placeholder', ''),
                    'label': self._get_input_label(input_elem)
                }
                form_info['inputs'].append(input_info)
            
            forms.append(form_info)
        return forms[:5]
    
    def _get_input_label(self, input_elem) -> str:
        input_id = input_elem.get('id')
        if input_id:
            label = input_elem.find_parent().find('label', {'for': input_id})
            if label:
                return label.get_text(strip=True)
        parent = input_elem.find_parent('label')
        if parent:
            return parent.get_text(strip=True)
        
        return ''
    
    def _extract_main_text(self, soup: BeautifulSoup) -> str:
        for elem in soup.find_all(['nav', 'footer', 'header', 'aside']):
            elem.decompose()
        text = soup.get_text(separator=' ', strip=True)
        text = re.sub(r'\s+', ' ', text)
        return text[:500]
    
    def _extract_interactive_elements(self, soup: BeautifulSoup) -> list:
        elements = []
        clickable_selectors = [
            '[onclick]',
            '[role="button"]',
            '[role="link"]',
            '.btn',
            '.button',
            '.clickable',
            '[data-testid]',
            '[data-qa]'
        ]
        
        for selector in clickable_selectors:
            for elem in soup.select(selector):
                text = elem.get_text(strip=True) or elem.get('aria-label', '')
                if text:
                    elements.append({
                        'text': text[:100],
                        'selector': selector,
                        'id': elem.get('id', ''),
                        'class': ' '.join(elem.get('class', []))
                    })
        
        return elements[:15]
    

