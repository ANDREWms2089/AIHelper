import os
from typing import List, Dict, Optional
from browser_controller import BrowserController
from page_analyzer import PageAnalyzer
from security_layer import SecurityLayer
from context_manager import ContextManager
from element_finder import ElementFinder
from ai_providers import get_ai_provider, BaseAIProvider
from guardrails import GuardrailsSystem, RiskLevel
import json
import asyncio


class AIAgent:
    def __init__(self, provider: str = 'groq', **provider_kwargs):
        self.ai_provider: BaseAIProvider = get_ai_provider(provider, **provider_kwargs)
        self.provider_name = provider
        self.browser_controller: Optional[BrowserController] = None
        self.page_analyzer: Optional[PageAnalyzer] = None
        self.element_finder: Optional[ElementFinder] = None
        self.context_manager = ContextManager()
        self.guardrails = GuardrailsSystem()
        
    def set_browser(self, browser_controller: BrowserController):
        self.browser_controller = browser_controller
        if browser_controller.page:
            self.page_analyzer = PageAnalyzer(browser_controller.page)
            self.element_finder = ElementFinder(browser_controller.page)
        else:
            self.element_finder = None
    
    def get_tools(self) -> List[Dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "navigate_to_url",
                    "description": "Перейти на указанный URL",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "URL для перехода"
                            }
                        },
                        "required": ["url"]
                    }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "click_element",
                "description": "Кликнуть на элемент страницы. Используй текст элемента или его описание для поиска",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "element_text": {
                            "type": "string",
                            "description": "Текст или описание элемента для клика (например, 'кнопка Войти', 'ссылка Вакансии')"
                        },
                        "selector": {
                            "type": "string",
                            "description": "CSS селектор элемента (опционально, если известен)"
                        }
                    },
                    "required": ["element_text"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "type_text",
                "description": "Ввести текст в поле ввода",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "field_description": {
                            "type": "string",
                            "description": "Описание поля (например, 'поле email', 'поле пароль')"
                        },
                        "text": {
                            "type": "string",
                            "description": "Текст для ввода"
                        },
                        "selector": {
                            "type": "string",
                            "description": "CSS селектор поля (опционально)"
                        }
                    },
                    "required": ["field_description", "text"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_page_info",
                "description": "Получить информацию о текущей странице (ссылки, кнопки, формы)",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "wait",
                "description": "Подождать указанное время (в секундах)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "seconds": {
                            "type": "number",
                            "description": "Количество секунд для ожидания"
                        }
                    },
                    "required": ["seconds"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "scroll",
                "description": "Прокрутить страницу вниз или вверх",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "direction": {
                            "type": "string",
                            "enum": ["down", "up"],
                            "description": "Направление прокрутки"
                        },
                        "amount": {
                            "type": "number",
                            "description": "Количество пикселей для прокрутки (по умолчанию 500)"
                        }
                    },
                    "required": ["direction"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "task_complete",
                "description": "Сообщить, что задача выполнена и предоставить результат",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "result": {
                            "type": "string",
                            "description": "Описание результата выполнения задачи"
                        }
                    },
                    "required": ["result"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "ask_user",
                "description": "Запросить дополнительную информацию у пользователя, если задача не может быть выполнена без неё",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "Вопрос для пользователя"
                        }
                    },
                    "required": ["question"]
                }
            }
        }
    ]
    
    async def execute_function(self, function_name: str, arguments: dict) -> str:
        tool_passed, tool_reason, tool_risk = self.guardrails.check_tool(function_name, arguments)
        
        if not tool_passed:
            if tool_risk == RiskLevel.CRITICAL:
                return f"❌ БЛОКИРОВАНО: {tool_reason}"
            elif tool_risk == RiskLevel.HIGH:
                print(f"⚠️  ВНИМАНИЕ: {tool_reason}")
                if not await SecurityLayer.check_and_confirm(f"Выполнить {function_name}", str(arguments)):
                    return f"❌ Действие отменено пользователем: {tool_reason}"
        page = self.browser_controller.page
        
        if function_name == "navigate_to_url":
            url = arguments.get("url")
            await self.browser_controller.navigate(url)
            await asyncio.sleep(2)
            
            captcha_info = await self.browser_controller.check_captcha()
            if captcha_info['has_captcha']:
                print(f"\n⚠️  {captcha_info['message']}")
                await self.browser_controller.wait_for_captcha_completion()
            
            captcha_info = await self.browser_controller.check_captcha()
            if captcha_info['has_captcha']:
                print(f"\n⚠️  {captcha_info['message']}")
                await self.browser_controller.wait_for_captcha_completion()
            
            login_status = await self.browser_controller.check_login_status()
            if login_status['has_login_form'] and not login_status['is_logged_in']:
                print("\n🔐 Обнаружена форма входа после перехода на сайт. Ожидаю успешного входа...")
                login_success = await self.browser_controller.wait_for_login()
                if login_success:
                    await asyncio.sleep(1)
                    if self.page_analyzer:
                        page_info = await self.page_analyzer.get_page_summary()
                        self.context_manager.update_page_info(page_info)
            
            if self.page_analyzer:
                page_info = await self.page_analyzer.get_page_summary()
                self.context_manager.update_page_info(page_info)
            return f"Перешел на {url}"
        
        elif function_name == "click_element":
            element_text = arguments.get("element_text", "")
            selector = arguments.get("selector")
            
            # Проверяем безопасность
            if not await SecurityLayer.check_and_confirm("click", element_text):
                return "Действие отменено пользователем"
            
            try:
                # Пытаемся найти элемент по тексту
                if selector:
                    try:
                        await page.click(selector)
                    except:
                        return f"Не удалось кликнуть по селектору '{selector}'"
                else:
                    # Используем улучшенный поиск элементов
                    if self.element_finder:
                        found = await self.element_finder.find_clickable_element(element_text)
                        if found and found.get('element'):
                            await found['element'].click()
                        else:
                            return f"Не удалось найти элемент с текстом '{element_text}'. Попробуй получить информацию о странице через get_page_info."
                    else:
                        return "Element finder не инициализирован"
                
                await asyncio.sleep(1)  # Ждем после клика
                
                # Проверяем наличие капчи после клика
                captcha_info = await self.browser_controller.check_captcha()
                if captcha_info['has_captcha']:
                    print(f"\n⚠️  {captcha_info['message']}")
                    await self.browser_controller.wait_for_captcha_completion()
                
                # Обновляем информацию о странице
                if self.page_analyzer:
                    page_info = await self.page_analyzer.get_page_summary()
                    self.context_manager.update_page_info(page_info)
                
                return f"Кликнул на '{element_text}'"
            except Exception as e:
                return f"Ошибка при клике: {str(e)}"
        
        elif function_name == "type_text":
            field_description = arguments.get("field_description", "")
            text = arguments.get("text", "")
            selector = arguments.get("selector")
            
            try:
                if selector:
                    try:
                        await page.fill(selector, text)
                    except:
                        return f"Не удалось заполнить поле по селектору '{selector}'"
                else:
                    # Используем улучшенный поиск полей
                    if self.element_finder:
                        found = await self.element_finder.find_input_field(field_description)
                        if found and found.get('element'):
                            await found['element'].fill(text)
                        else:
                            return f"Не удалось найти поле '{field_description}'. Попробуй получить информацию о странице через get_page_info."
                    else:
                        return "Element finder не инициализирован"
                
                return f"Ввел '{text}' в поле '{field_description}'"
            except Exception as e:
                return f"Ошибка при вводе текста: {str(e)}"
        
        elif function_name == "get_page_info":
            if self.page_analyzer:
                page_info = await self.page_analyzer.get_page_summary()
                self.context_manager.update_page_info(page_info)
                return json.dumps(page_info, ensure_ascii=False, indent=2)
            return "Page analyzer не инициализирован"
        
        elif function_name == "wait":
            seconds = arguments.get("seconds", 1)
            await asyncio.sleep(seconds)
            return f"Подождал {seconds} секунд"
        
        elif function_name == "scroll":
            direction = arguments.get("direction", "down")
            amount = arguments.get("amount", 500)
            
            if direction == "down":
                await page.evaluate(f"window.scrollBy(0, {amount})")
            else:
                await page.evaluate(f"window.scrollBy(0, -{amount})")
            
            await asyncio.sleep(0.5)
            return f"Прокрутил страницу {direction} на {amount}px"
        
        elif function_name == "task_complete":
            result = arguments.get("result", "")
            return f"✅ Задача выполнена: {result}"
        
        elif function_name == "ask_user":
            question = arguments.get("question", "")
            return f"❓ Вопрос пользователю: {question}"
        
        return f"Неизвестная функция: {function_name}"
    
    async def process_task(self, task: str) -> str:
        print(f"\n🤖 Начинаю выполнение задачи: {task}\n")
        
        # Инициализируем контекст
        system_prompt = """Ты автономный AI-агент, который управляет браузером для выполнения задач пользователя.

Твои возможности:
- Переходить на страницы
- Кликать на элементы (кнопки, ссылки)
- Вводить текст в поля
- Получать информацию о странице
- Прокручивать страницу

КРИТИЧЕСКИ ВАЖНЫЕ ПРАВИЛА:
1. Анализируй задачу пользователя и выполняй ТОЛЬКО необходимые действия для её выполнения
2. НЕ делай лишних кликов и переходов - если задача уже выполнена, используй task_complete
3. Если ты на странице с результатами поиска и нашел нужный контент - задача выполнена, используй task_complete
4. НЕ переходи по ссылкам "Каталог", "О нас", "Контакты" и другим, если они не нужны для выполнения задачи
5. Если задача - найти что-то на сайте, используй поиск или фильтры, а не навигационное меню
6. После каждого действия проверяй, выполнена ли задача - если да, используй task_complete
7. НЕ используй заготовленные планы - адаптируйся к ситуации
8. НЕ используй хардкоженные селекторы - находи элементы по их тексту и описанию
9. Если не можешь найти элемент, попробуй разные способы (текст, aria-label, классы)
10. Если задача требует деструктивного действия (оплата, удаление), система спросит подтверждение
11. Если нужна дополнительная информация от пользователя, используй ask_user

Начни с получения информации о текущей странице, если она уже открыта."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task}
        ]
        
        max_iterations = 50
        iteration = 0
        login_checked = False
        recent_actions = []
        last_page_info = None
        consecutive_same_actions = 0
        task_completed = False
        last_successful_result = None
        consecutive_success_count = 0
        
        while iteration < max_iterations and not task_completed:
            iteration += 1
            print(f"\n[Итерация {iteration}]")
            
            try:
                if not login_checked:
                    login_status = await self.browser_controller.check_login_status()
                    if login_status['has_login_form'] and not login_status['is_logged_in']:
                        print("\n🔐 Обнаружена форма входа. Ожидаю успешного входа...")
                        login_success = await self.browser_controller.wait_for_login()
                        login_checked = True
                        if login_success:
                            await asyncio.sleep(1)
                            if self.page_analyzer:
                                page_info = await self.page_analyzer.get_page_summary()
                                self.context_manager.update_page_info(page_info)
                            messages.append({"role": "user", "content": "Вход выполнен успешно. Продолжи выполнение задачи."})
                        continue
                    else:
                        login_checked = True
                
                captcha_info = await self.browser_controller.check_captcha()
                if captcha_info['has_captcha']:
                    print(f"\n⚠️  {captcha_info['message']}")
                    await self.browser_controller.wait_for_captcha_completion()
                
                # Вызываем AI через провайдер
                tools = self.get_tools()
                response = await self.ai_provider.chat_completion(
                    messages=messages,
                    tools=tools,
                    tool_choice="auto"
                )
                
                content = response.get('content', '')
                tool_calls = response.get('tool_calls', [])
                
                if content:
                    output_passed, output_errors = self.guardrails.check_output(content)
                    if not output_passed:
                        print(f"⚠️  Предупреждения системы безопасности:")
                        for err in output_errors:
                            print(f"  - {err}")
                
                # Форматируем tool_calls для OpenAI API (добавляем поле type)
                formatted_tool_calls = []
                if tool_calls:
                    for tc in tool_calls:
                        formatted_tool_calls.append({
                            "id": tc.get('id', ''),
                            "type": "function",  # Обязательное поле для OpenAI API
                            "function": tc.get('function', {})
                        })
                
                # Добавляем ответ AI в контекст
                assistant_message = {
                    "role": "assistant",
                    "content": content or None
                }
                if formatted_tool_calls:
                    assistant_message["tool_calls"] = formatted_tool_calls
                
                messages.append(assistant_message)
                
                # Если есть tool calls, выполняем их
                if tool_calls:
                    for tool_call in tool_calls:
                        function_name = tool_call['function']['name']
                        tool_call_id = tool_call.get('id', '')
                        
                        try:
                            arguments = json.loads(tool_call['function']['arguments'])
                        except:
                            arguments = tool_call['function'].get('arguments', {})
                            if isinstance(arguments, str):
                                try:
                                    arguments = json.loads(arguments)
                                except:
                                    arguments = {}
                        
                        print(f"🔧 Вызываю: {function_name}({json.dumps(arguments, ensure_ascii=False)})")
                        
                        action_key = f"{function_name}:{json.dumps(arguments, sort_keys=True)}"
                        
                        if len(recent_actions) > 0 and recent_actions[-1] == action_key:
                            consecutive_same_actions += 1
                            if consecutive_same_actions >= 2:
                                print("⚠️  Обнаружено повторение одних и тех же действий. Завершаю выполнение.")
                                task_completed = True
                                return f"⚠️  Прервано из-за повторяющихся действий."
                        else:
                            consecutive_same_actions = 0
                        
                        recent_actions.append(action_key)
                        if len(recent_actions) > 5:
                            recent_actions.pop(0)
                        
                        try:
                            result = await self.execute_function(function_name, arguments)
                            print(f"   Результат: {result}")
                            
                            if function_name == "get_page_info":
                                current_page_info = result
                                if last_page_info and current_page_info == last_page_info:
                                    result_str = str(result)
                                    result_lower = result_str.lower()
                                    task_lower = task.lower()
                                    
                                    if any(keyword in result_lower for keyword in ["додж", "dodge", "challenger", "челенджер", "челленджер"]):
                                        if any(keyword in result_lower for keyword in ["цена", "стоимость", "руб", "₽"]):
                                            print("✅ Найден искомый контент, страница не изменилась. Завершаю выполнение.")
                                            task_completed = True
                                            return f"✅ Задача выполнена: найден {task_lower.split('найди')[1] if 'найди' in task_lower else 'искомый контент'}"
                                    
                                    if "найден" in result_lower or "нашел" in result_lower or "найдено" in result_lower:
                                        print("✅ Контент уже найден, страница не изменилась. Завершаю выполнение.")
                                        task_completed = True
                                        return f"✅ Задача выполнена: {result}"
                                last_page_info = current_page_info
                            
                            result_lower = str(result).lower()
                            task_lower = task.lower()
                            success_indicators = ["найден", "нашел", "найдено", "успешно", "готово", "выполнено", "завершено"]
                            
                            if function_name == "get_page_info":
                                result_str = str(result)
                                if any(keyword in task_lower for keyword in ["найди", "найти", "найди там"]):
                                    search_keywords = []
                                    if "додж" in task_lower or "dodge" in task_lower:
                                        search_keywords.extend(["додж", "dodge"])
                                    if "челенджер" in task_lower or "challenger" in task_lower or "челленджер" in task_lower:
                                        search_keywords.extend(["challenger", "челенджер", "челленджер"])
                                    
                                    if search_keywords and any(keyword in result_str.lower() for keyword in search_keywords):
                                        if "цена" in result_str.lower() or "стоимость" in result_str.lower() or "руб" in result_str.lower():
                                            print("✅ Найден искомый контент на странице. Завершаю выполнение.")
                                            task_completed = True
                                            return f"✅ Задача выполнена: найден {task_lower.split('найди')[1] if 'найди' in task_lower else 'искомый контент'}"
                            
                            if any(indicator in result_lower for indicator in success_indicators):
                                if function_name in ["get_page_info", "click_element", "navigate_to_url", "scroll"]:
                                    if last_successful_result == result:
                                        consecutive_success_count += 1
                                        if consecutive_success_count >= 2:
                                            print("✅ Обнаружен повторяющийся успешный результат. Завершаю выполнение.")
                                            task_completed = True
                                            return f"✅ Задача выполнена: {result}"
                                    else:
                                        consecutive_success_count = 1
                                        last_successful_result = result
                                    
                                    if "найден" in result_lower or "нашел" in result_lower or "найдено" in result_lower:
                                        print("✅ Обнаружен успешный результат. Завершаю выполнение.")
                                        task_completed = True
                                        return f"✅ Задача выполнена: {result}"
                        except Exception as e:
                            result = f"Ошибка при выполнении функции {function_name}: {str(e)}"
                            print(f"   ❌ Ошибка: {result}")
                        
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "content": result
                        })
                        
                        if function_name == "task_complete":
                            task_completed = True
                            return result
                        elif function_name == "ask_user":
                            # Запрашиваем ответ у пользователя
                            user_response = input(f"\n{result}\nВаш ответ: ")
                            messages.append({
                                "role": "user",
                                "content": user_response
                            })
                
                # Если нет tool calls и есть текстовый ответ
                elif content:
                    print(f"💬 {content}")
                    content_lower = content.lower()
                    completion_keywords = ["выполнена", "завершена", "готово", "найдено", "нашел", "найден", "успешно"]
                    if any(keyword in content_lower for keyword in completion_keywords):
                        if "найдено" in content_lower or "нашел" in content_lower or "найден" in content_lower:
                            print("✅ Агент сообщил об успешном выполнении. Завершаю выполнение.")
                            task_completed = True
                            return content
                
            except Exception as e:
                error_msg = str(e)
                print(f"❌ Ошибка: {error_msg}")
                
                # Проверяем ошибки API провайдера
                if ("403" in error_msg or "402" in error_msg or 
                    "permission" in error_msg.lower() or 
                    "credits" in error_msg.lower() or 
                    "licenses" in error_msg.lower() or
                    "insufficient balance" in error_msg.lower() or
                    "insufficient" in error_msg.lower()):
                    print("\n⚠️  ПРОБЛЕМА С API ПРОВАЙДЕРОМ!")
                    print("   Похоже, у вашего аккаунта нет кредитов, баланса или доступа.")
                    print("   Рекомендуется переключиться на бесплатный провайдер:")
                    print("   - Groq (бесплатный): https://console.groq.com/")
                    print("   - Ollama (локальный, полностью бесплатный): https://ollama.ai/")
                    print("\n   См. инструкции в SWITCH_TO_GROQ.md")
                    return f"Ошибка API провайдера: {error_msg}. Переключитесь на бесплатный провайдер (Groq или Ollama)."
                
                # Адаптация: добавляем контекст об ошибке и предлагаем альтернативы
                error_context = f"Произошла ошибка: {error_msg}. "
                
                # Анализируем тип ошибки и предлагаем решение
                if "не удалось найти" in error_msg.lower() or "not found" in error_msg.lower():
                    error_context += "Попробуй получить актуальную информацию о странице через get_page_info, чтобы увидеть доступные элементы."
                elif "timeout" in error_msg.lower() or "waiting" in error_msg.lower():
                    error_context += "Страница может загружаться медленно. Попробуй подождать несколько секунд через wait."
                elif "click" in error_msg.lower() or "клик" in error_msg.lower():
                    error_context += "Элемент может быть не виден или перекрыт. Попробуй прокрутить страницу через scroll или найти элемент другим способом."
                else:
                    error_context += "Попробуй другой подход или получи информацию о текущем состоянии страницы."
                
                messages.append({
                    "role": "user",
                    "content": error_context
                })
                
                # Ограничиваем количество ошибок подряд
                if iteration > 5:
                    consecutive_errors = sum(1 for msg in messages[-5:] if "ошибка" in msg.get('content', '').lower() or "error" in msg.get('content', '').lower())
                    if consecutive_errors >= 3:
                        return f"Слишком много ошибок подряд. Возможно, задача требует дополнительной информации или другого подхода. Последняя ошибка: {error_msg}"
        
        return "Достигнуто максимальное количество итераций. Задача может быть не завершена."

