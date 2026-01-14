import asyncio
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from pathlib import Path


class BrowserController:
    def __init__(self, headless: bool = False, user_data_dir: str = None):
        self.headless = headless
        self.user_data_dir = user_data_dir or str(Path.home() / ".browser-ai-agent")
        self.playwright = None
        self.browser: Browser = None
        self.context: BrowserContext = None
        self.page: Page = None
        
    async def start(self, start_url: str = None):
        self.playwright = await async_playwright().start()
        browser_args = []
        if not self.headless:
            browser_args = [
                '--start-maximized',
                '--start-fullscreen'
            ]
        
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=browser_args
        )
        
        if not self.headless:
            self.context = await self.browser.new_context(
                viewport=None,
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                no_viewport=True
            )
        else:
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
        
        self.page = await self.context.new_page()
        
        if not self.headless:
            await self.page.evaluate("window.moveTo(0, 0); window.resizeTo(screen.width, screen.height);")
        
        if start_url:
            await self.navigate(start_url)
        
        return self.page
    
    async def close(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def navigate(self, url: str, timeout: int = 60000):
        try:
            await self.page.goto(url, wait_until='networkidle', timeout=timeout)
        except Exception as e:
            try:
                await self.page.goto(url, wait_until='domcontentloaded', timeout=timeout)
            except:
                await self.page.goto(url, wait_until='load', timeout=timeout)
                await asyncio.sleep(2)
    
    def get_page(self) -> Page:
        return self.page
    
    async def check_captcha(self) -> dict:
        captcha_info = {
            'has_captcha': False,
            'type': None,
            'message': None
        }
        
        try:
            recaptcha = await self.page.query_selector('.g-recaptcha, #recaptcha, [data-sitekey]')
            if recaptcha:
                captcha_info['has_captcha'] = True
                captcha_info['type'] = 'reCAPTCHA'
                captcha_info['message'] = 'Обнаружена reCAPTCHA. Пожалуйста, пройдите проверку в браузере.'
                return captcha_info
            
            hcaptcha = await self.page.query_selector('.h-captcha, [data-sitekey*="hcaptcha"]')
            if hcaptcha:
                captcha_info['has_captcha'] = True
                captcha_info['type'] = 'hCaptcha'
                captcha_info['message'] = 'Обнаружена hCaptcha. Пожалуйста, пройдите проверку в браузере.'
                return captcha_info
            
            page_text = await self.page.evaluate("document.body.innerText")
            cloudflare_indicators = [
                'checking your browser',
                'just a moment',
                'please wait',
                'ddos protection',
                'cloudflare'
            ]
            if any(indicator in page_text.lower() for indicator in cloudflare_indicators):
                cf_challenge = await self.page.query_selector('#challenge-form, .cf-browser-verification, [data-ray]')
                if cf_challenge:
                    captcha_info['has_captcha'] = True
                    captcha_info['type'] = 'Cloudflare'
                    captcha_info['message'] = 'Обнаружена проверка Cloudflare. Пожалуйста, дождитесь завершения проверки в браузере.'
                    return captcha_info
            
            captcha_keywords = ['captcha', 'verify you are human', 'i am not a robot', 'robot check']
            if any(keyword in page_text.lower() for keyword in captcha_keywords):
                captcha_iframe = await self.page.query_selector('iframe[src*="recaptcha"], iframe[src*="hcaptcha"], iframe[src*="captcha"]')
                if captcha_iframe:
                    captcha_info['has_captcha'] = True
                    captcha_info['type'] = 'Generic Captcha'
                    captcha_info['message'] = 'Обнаружена проверка на бота. Пожалуйста, пройдите проверку в браузере.'
                    return captcha_info
            
        except Exception as e:
            pass
        
        return captcha_info
    
    async def wait_for_captcha_completion(self, timeout: int = 300) -> bool:
        print("\n" + "="*60)
        print("🛡️  ОБНАРУЖЕНА ПРОВЕРКА НА БОТА!")
        print("="*60)
        print("Пожалуйста, пройдите проверку в открытом браузере.")
        print("Агент будет ждать, пока вы не пройдёте проверку...")
        print("💡 Нажмите Enter, чтобы пропустить ожидание капчи")
        print("="*60 + "\n")
        
        initial_url = self.page.url
        start_time = asyncio.get_event_loop().time()
        last_check_time = start_time
        skip_requested = False
        
        async def check_user_input():
            nonlocal skip_requested
            try:
                import sys
                import select
                if sys.stdin.isatty():
                    import termios
                    import tty
                    old_settings = termios.tcgetattr(sys.stdin)
                    try:
                        tty.setraw(sys.stdin.fileno())
                        if select.select([sys.stdin], [], [], 0.1)[0]:
                            char = sys.stdin.read(1)
                            if char == '\n' or char == '\r':
                                skip_requested = True
                    finally:
                        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            except:
                pass
        
        try:
            while True:
                await asyncio.sleep(0.5)
                await check_user_input()
                
                if skip_requested:
                    print("\n⏭️  Пропуск ожидания капчи по запросу пользователя")
                    print("="*60 + "\n")
                    return False
                
                await asyncio.sleep(2.5)
                
                current_url = self.page.url
                url_changed = current_url != initial_url
                
                if url_changed:
                    print("\n✅ Обнаружено изменение URL. Проверяю статус...")
                    await asyncio.sleep(2)
                    captcha_info = await self.check_captcha()
                    if not captcha_info['has_captcha']:
                        print("\n✅ Проверка пройдена! Продолжаю работу...\n")
                        return True
                    initial_url = current_url
                
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed >= timeout:
                    print(f"\n⏱️  Превышено время ожидания ({timeout} секунд)")
                    print("Продолжаю работу, но проверка может быть не пройдена.\n")
                    return False
                
                check_elapsed = asyncio.get_event_loop().time() - last_check_time
                if check_elapsed >= 10:
                    try:
                        captcha_info = await self.check_captcha()
                        if not captcha_info['has_captcha']:
                            print("\n✅ Проверка пройдена! Продолжаю работу...\n")
                            return True
                    except:
                        pass
                    last_check_time = asyncio.get_event_loop().time()
                    remaining = int(timeout - elapsed)
                    print(f"⏳ Ожидание прохождения капчи... (осталось ~{remaining} сек) | Нажмите Enter для пропуска")
        
        except Exception as e:
            print(f"\n⚠️  Ошибка при ожидании капчи: {e}")
            return False
    
    async def check_login_status(self) -> dict:
        login_status = {
            'is_logged_in': False,
            'has_login_form': False,
            'indicators': []
        }
        
        try:
            page_text = await self.page.evaluate("document.body.innerText")
            page_url = self.page.url.lower()
            
            logged_in_indicators = [
                'профиль', 'profile', 'личный кабинет', 'выход', 'logout',
                'настройки', 'settings', 'аккаунт', 'account', 'мой профиль',
                'добро пожаловать', 'welcome', 'ваши', 'мои'
            ]
            
            has_login_url = any(path in page_url for path in ['/login', '/signin', '/auth', '/войти', '/вход', '/sign-in', '/log-in'])
            
            email_inputs = await self.page.query_selector_all('input[type="email"], input[type="text"][name*="email" i], input[type="text"][name*="login" i], input[type="tel"], input[type="text"][placeholder*="email" i], input[type="text"][placeholder*="телефон" i], input[type="text"][placeholder*="phone" i]')
            password_inputs = await self.page.query_selector_all('input[type="password"]')
            
            has_email_field = len(email_inputs) > 0
            has_password_field = len(password_inputs) > 0
            
            login_buttons = await self.page.query_selector_all('button:has-text("войти"), button:has-text("вход"), button:has-text("login"), button:has-text("sign in"), button[type="submit"], input[type="submit"]')
            has_login_button = len(login_buttons) > 0
            
            if has_login_url:
                login_status['has_login_form'] = True
                login_status['indicators'].append('URL указывает на страницу входа')
            elif has_email_field and has_password_field:
                login_status['has_login_form'] = True
                login_status['indicators'].append('Обнаружена форма входа (email/телефон + пароль)')
            elif has_email_field and has_password_field and has_login_button:
                login_status['has_login_form'] = True
                login_status['indicators'].append('Обнаружена форма входа (поля + кнопка)')
            
            has_logged_in_text = any(indicator in page_text.lower() for indicator in logged_in_indicators)
            
            profile_elements = await self.page.query_selector_all('[class*="profile" i], [class*="user" i], [class*="account" i], [id*="profile" i], [id*="user" i], [id*="account" i]')
            has_profile_elements = len(profile_elements) > 0
            
            logout_buttons = await self.page.query_selector_all('button:has-text("выход"), button:has-text("logout"), a:has-text("выход"), a:has-text("logout")')
            has_logout = len(logout_buttons) > 0
            
            if has_logged_in_text or has_profile_elements or has_logout:
                login_status['is_logged_in'] = True
                if has_logged_in_text:
                    login_status['indicators'].append('Обнаружен текст, указывающий на вход')
                if has_profile_elements:
                    login_status['indicators'].append('Обнаружены элементы профиля')
                if has_logout:
                    login_status['indicators'].append('Обнаружена кнопка выхода')
            
            if not login_status['has_login_form']:
                if has_logged_in_text or has_profile_elements:
                    login_status['is_logged_in'] = True
                    login_status['indicators'].append('Форма входа отсутствует, обнаружены признаки авторизации')
        
        except Exception as e:
            pass
        
        return login_status
    
    async def wait_for_login(self, timeout: int = 600) -> bool:
        print("\n" + "="*60)
        print("🔐 ОЖИДАНИЕ ВХОДА В АККАУНТ")
        print("="*60)
        print("Пожалуйста, войдите в свой аккаунт в открытом браузере.")
        print("Агент будет ждать успешного входа...")
        print("💡 Нажмите Enter, чтобы пропустить ожидание входа")
        print("="*60 + "\n")
        
        initial_url = self.page.url
        start_time = asyncio.get_event_loop().time()
        last_check_time = start_time
        last_status = None
        skip_requested = False
        
        async def check_user_input():
            nonlocal skip_requested
            try:
                import sys
                import select
                if sys.stdin.isatty():
                    import termios
                    import tty
                    old_settings = termios.tcgetattr(sys.stdin)
                    try:
                        tty.setraw(sys.stdin.fileno())
                        if select.select([sys.stdin], [], [], 0.1)[0]:
                            char = sys.stdin.read(1)
                            if char == '\n' or char == '\r':
                                skip_requested = True
                    finally:
                        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            except:
                pass
        
        try:
            while True:
                await asyncio.sleep(0.5)
                await check_user_input()
                
                if skip_requested:
                    print("\n⏭️  Пропуск ожидания входа по запросу пользователя")
                    print("="*60 + "\n")
                    return False
                
                await asyncio.sleep(2.5)
                
                current_url = self.page.url
                url_changed = current_url != initial_url
                
                if url_changed:
                    print(f"\n🔄 Обнаружено изменение URL: {current_url}")
                    await asyncio.sleep(2)
                    login_status = await self.check_login_status()
                    
                    if login_status['is_logged_in'] and not login_status['has_login_form']:
                        print("\n✅ Успешный вход обнаружен!")
                        if login_status['indicators']:
                            print(f"   Признаки: {', '.join(login_status['indicators'])}")
                        print("="*60 + "\n")
                        return True
                    
                    initial_url = current_url
                
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed >= timeout:
                    print(f"\n⏱️  Превышено время ожидания входа ({timeout} секунд)")
                    print("Продолжаю работу, но вход может быть не выполнен.\n")
                    print("="*60 + "\n")
                    return False
                
                check_elapsed = asyncio.get_event_loop().time() - last_check_time
                if check_elapsed >= 10:
                    try:
                        login_status = await self.check_login_status()
                        if login_status['is_logged_in'] and not login_status['has_login_form']:
                            print("\n✅ Успешный вход обнаружен!")
                            if login_status['indicators']:
                                print(f"   Признаки: {', '.join(login_status['indicators'])}")
                            print("="*60 + "\n")
                            return True
                        
                        status_str = f"Вход: {'✅' if login_status['is_logged_in'] else '⏳'}, Форма входа: {'✅' if login_status['has_login_form'] else '❌'}"
                        if status_str != last_status:
                            remaining = int(timeout - elapsed)
                            print(f"⏳ {status_str} (осталось ~{remaining} сек) | Нажмите Enter для пропуска")
                            last_status = status_str
                    except:
                        pass
                    last_check_time = asyncio.get_event_loop().time()
        
        except Exception as e:
            print(f"\n⚠️  Ошибка при ожидании входа: {e}")
            return False

