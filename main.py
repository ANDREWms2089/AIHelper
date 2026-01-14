import asyncio
import os
from dotenv import load_dotenv
from browser_controller import BrowserController
from ai_agent import AIAgent
from config import (
    AI_PROVIDER,
    OPENROUTER_API_KEY, OPENROUTER_MODEL,
    BROWSER_HEADLESS, BROWSER_START_URL, MAX_ITERATIONS
)


async def main():
    load_dotenv()
    
    print("🚀 Запуск Browser AI Agent...")
    print(f"📡 Используется провайдер: {AI_PROVIDER.upper()}")
    print("=" * 50)
    
    if not OPENROUTER_API_KEY:
        print("❌ Ошибка: OPENROUTER_API_KEY не найден в .env файле")
        return
    
    print("🚀 Используется OpenRouter провайдер")
    print(f"   Модель: {OPENROUTER_MODEL}")
    print("💡 OpenRouter предоставляет доступ к множеству AI моделей")
    
    provider_kwargs = {'api_key': OPENROUTER_API_KEY, 'model': OPENROUTER_MODEL}
    
    browser = BrowserController(headless=BROWSER_HEADLESS)
    await browser.start(start_url=BROWSER_START_URL if BROWSER_START_URL != 'about:blank' else None)
    
    print("✅ Браузер запущен")
    print("💡 Подсказка: Вы можете войти в аккаунты вручную, агент продолжит работу")
    print("=" * 50)
    
    try:
        agent = AIAgent(provider=AI_PROVIDER, **provider_kwargs)
        agent.set_browser(browser)
        print(f"✅ AI агент инициализирован с провайдером {AI_PROVIDER}")
    except Exception as e:
        print(f"❌ Ошибка инициализации AI агента: {e}")
        await browser.close()
        return
    
    if agent.page_analyzer:
        page_info = await agent.page_analyzer.get_page_summary()
        agent.context_manager.update_page_info(page_info)
    
    print("\n🤖 Агент готов к работе!")
    print("Введите задачу для выполнения (или 'quit' для выхода):\n")
    
    try:
        while True:
            task = input("> ").strip()
            
            if task.lower() in ['quit', 'exit', 'q']:
                break
            
            if not task:
                continue
            
            result = await agent.process_task(task)
            print(f"\n{result}\n")
            print("-" * 50)
            print("Введите следующую задачу (или 'quit' для выхода):\n")
    
    except KeyboardInterrupt:
        print("\n\n👋 Завершение работы...")
    finally:
        await browser.close()
        print("✅ Браузер закрыт")


if __name__ == "__main__":
    asyncio.run(main())
