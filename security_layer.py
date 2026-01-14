import re


class SecurityLayer:
    # Паттерны деструктивных действий
    DESTRUCTIVE_KEYWORDS = [
        'delete', 'remove', 'cancel', 'unsubscribe',
        'pay', 'purchase', 'buy', 'checkout', 'order',
        'confirm', 'submit payment', 'place order',
        'send money', 'transfer', 'withdraw'
    ]
    
    # Паттерны опасных текстов на кнопках
    DANGEROUS_BUTTON_TEXT = [
        r'delete',
        r'remove',
        r'cancel.*subscription',
        r'pay.*now',
        r'purchase',
        r'buy.*now',
        r'checkout',
        r'place.*order',
        r'confirm.*payment',
        r'send.*money'
    ]
    
    @classmethod
    def is_destructive_action(cls, action: str, element_text: str = '') -> bool:
        action_lower = action.lower()
        text_lower = element_text.lower()
        
        # Проверяем ключевые слова в действии
        for keyword in cls.DESTRUCTIVE_KEYWORDS:
            if keyword in action_lower:
                return True
        
        # Проверяем текст элемента
        for pattern in cls.DANGEROUS_BUTTON_TEXT:
            if re.search(pattern, text_lower):
                return True
        
        return False
    
    @classmethod
    async def check_and_confirm(cls, action: str, element_text: str = '') -> bool:
        if not cls.is_destructive_action(action, element_text):
            return True
        
        print(f"\n⚠️  ВНИМАНИЕ: Обнаружено потенциально опасное действие!")
        print(f"   Действие: {action}")
        if element_text:
            print(f"   Элемент: {element_text}")
        print(f"\n   Продолжить? (yes/no): ", end='', flush=True)
        
        try:
            response = input().strip().lower()
            return response in ['yes', 'y', 'да', 'д']
        except (EOFError, KeyboardInterrupt):
            print("\n   Действие отменено.")
            return False

