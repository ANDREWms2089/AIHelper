import os
import asyncio
from typing import List, Dict, Optional, Any
from openai import AsyncOpenAI
import json


class BaseAIProvider:
    async def chat_completion(self, messages: List[Dict], tools: List[Dict], tool_choice: str = "auto") -> Dict:
        raise NotImplementedError
    
    def format_tools(self, tools: List[Dict]) -> Any:
        return tools


class OpenRouterProvider(BaseAIProvider):
    def __init__(self, api_key: str, model: str = "openai/gpt-4o-mini"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1"
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            default_headers={
                "HTTP-Referer": "https://github.com/andrewvoevodin/browser-ai-agent",
                "X-Title": "Browser AI Agent"
            }
        )
        
        print(f"🔑 Инициализирован OpenRouter провайдер с моделью: {self.model}")
    
    async def chat_completion(self, messages: List[Dict], tools: List[Dict], tool_choice: str = "auto") -> Dict:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools if tools else None,
                tool_choice=tool_choice if tools else None
            )
            
            message = response.choices[0].message
            
            return {
                'content': message.content,
                'tool_calls': [
                    {
                        'id': tc.id,
                        'function': {
                            'name': tc.function.name,
                            'arguments': tc.function.arguments
                        }
                    } for tc in (message.tool_calls or [])
                ]
            }
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Ошибка OpenRouter: {error_msg}")
            raise RuntimeError(f"Ошибка OpenRouter: {error_msg}")


def get_ai_provider(provider_name: str, **kwargs) -> BaseAIProvider:
    provider_name = provider_name.lower()
    
    if provider_name == 'openrouter':
        return OpenRouterProvider(
            api_key=kwargs.get('api_key', ''),
            model=kwargs.get('model', 'openai/gpt-4o-mini')
        )
    
    raise ValueError(f"Неизвестный провайдер: {provider_name}")
