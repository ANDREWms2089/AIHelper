import os
from dotenv import load_dotenv

load_dotenv()

AI_PROVIDER = 'openrouter'

OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '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')
OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'openai/gpt-4o-mini')

BROWSER_HEADLESS = os.getenv('BROWSER_HEADLESS', 'false').lower() == 'true'
BROWSER_START_URL = os.getenv('BROWSER_START_URL', 'about:blank')

MAX_ITERATIONS = int(os.getenv('MAX_ITERATIONS', '50'))
MAX_CONTEXT_LENGTH = int(os.getenv('MAX_CONTEXT_LENGTH', '10000'))

AUTO_CONFIRM_DESTRUCTIVE = os.getenv('AUTO_CONFIRM_DESTRUCTIVE', 'false').lower() == 'true'
