from playwright.async_api import Page
import re


class ElementFinder:
    def __init__(self, page: Page):
        self.page = page
    
    async def find_clickable_element(self, text: str) -> dict:
        text_lower = text.lower().strip()
        try:
            selectors = [
                f'text="{text}"',
                f'text=/{re.escape(text)}/i',
                f'button:has-text("{text}")',
                f'a:has-text("{text}")',
                f'[role="button"]:has-text("{text}")',
                f'[role="link"]:has-text("{text}")'
            ]
            
            for selector in selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element and await element.is_visible():
                        return {
                            'element': element,
                            'selector': selector,
                            'method': 'text_match'
                        }
                except:
                    continue
        except Exception as e:
            pass
        try:
            words = text_lower.split()
            if len(words) > 0:
                main_word = words[0] if len(words[0]) > 3 else (words[1] if len(words) > 1 else words[0])
                
                selectors = [
                    f'button:has-text("{main_word}")',
                    f'a:has-text("{main_word}")',
                    f'[role="button"]:has-text("{main_word}")',
                    f'*:has-text("{main_word}")'
                ]
                
                for selector in selectors:
                    try:
                        elements = await self.page.query_selector_all(selector)
                        for elem in elements:
                            if await elem.is_visible():
                                elem_text = await elem.inner_text()
                                if text_lower in elem_text.lower() or elem_text.lower() in text_lower:
                                    return {
                                        'element': elem,
                                        'selector': selector,
                                        'method': 'partial_match'
                                    }
                    except:
                        continue
        except Exception as e:
            pass
        try:
            elements = await self.page.query_selector_all('[aria-label]')
            for elem in elements:
                aria_label = await elem.get_attribute('aria-label')
                if aria_label and text_lower in aria_label.lower():
                    if await elem.is_visible():
                        return {
                            'element': elem,
                            'selector': f'[aria-label*="{text}"]',
                            'method': 'aria_label'
                        }
        except:
            pass
        try:
            elements = await self.page.query_selector_all('[title]')
            for elem in elements:
                title = await elem.get_attribute('title')
                if title and text_lower in title.lower():
                    if await elem.is_visible():
                        return {
                            'element': elem,
                            'selector': f'[title*="{text}"]',
                            'method': 'title'
                        }
        except:
            pass
        try:
            text_escaped = text.replace("'", "\\'")
            xpath = f"//*[contains(text(), '{text_escaped}')]"
            elements = await self.page.query_selector_all(f"xpath={xpath}")
            
            for elem in elements:
                if await elem.is_visible():
                    tag_name = await elem.evaluate('el => el.tagName.toLowerCase()')
                    role = await elem.get_attribute('role')
                    
                    if tag_name in ['button', 'a', 'input'] or role in ['button', 'link']:
                        return {
                            'element': elem,
                            'selector': xpath,
                            'method': 'xpath'
                        }
        except:
            pass
        
        return None
    
    async def find_input_field(self, description: str) -> dict:
        desc_lower = description.lower()
        try:
            keywords = ['email', 'password', 'пароль', 'имя', 'name', 'телефон', 'phone']
            for keyword in keywords:
                if keyword in desc_lower:
                    selectors = [
                        f'input[placeholder*="{keyword}"]',
                        f'input[name*="{keyword}"]',
                        f'input[type="{keyword}"]',
                        f'input[id*="{keyword}"]'
                    ]
                    
                    for selector in selectors:
                        try:
                            elements = await self.page.query_selector_all(selector)
                            for elem in elements:
                                if await elem.is_visible():
                                    return {
                                        'element': elem,
                                        'selector': selector,
                                        'method': 'keyword_match'
                                    }
                        except:
                            continue
        except:
            pass
        type_mapping = {
            'email': 'email',
            'пароль': 'password',
            'password': 'password',
            'телефон': 'tel',
            'phone': 'tel'
        }
        
        for keyword, input_type in type_mapping.items():
            if keyword in desc_lower:
                try:
                    elements = await self.page.query_selector_all(f'input[type="{input_type}"]')
                    for elem in elements:
                        if await elem.is_visible():
                            return {
                                'element': elem,
                                'selector': f'input[type="{input_type}"]',
                                'method': 'type_match'
                            }
                except:
                    continue
        try:
            elements = await self.page.query_selector_all('input:visible, textarea:visible')
            for elem in elements:
                value = await elem.input_value()
                if not value:
                    return {
                        'element': elem,
                        'selector': 'first_empty_input',
                        'method': 'first_empty'
                    }
        except:
            pass
        
        return None

