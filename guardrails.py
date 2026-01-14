import re
from typing import Dict, List, Optional, Tuple
from enum import Enum


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class GuardrailResult:
    def __init__(self, passed: bool, risk_level: RiskLevel = RiskLevel.LOW, 
                 reason: str = "", blocked: bool = False):
        self.passed = passed
        self.risk_level = risk_level
        self.reason = reason
        self.blocked = blocked
    
    def __bool__(self):
        return self.passed and not self.blocked


class RelevanceClassifier:
    def __init__(self):
        self.off_topic_keywords = [
            'высота эмпайр стейт билдинг', 'empire state building',
            'сколько весит', 'какая температура', 'исторические факты',
            'математические задачи', 'физические законы', 'химические формулы'
        ]
    
    def check(self, input_text: str, task: str) -> GuardrailResult:
        input_lower = input_text.lower()
        task_lower = task.lower()
        
        for keyword in self.off_topic_keywords:
            if keyword in input_lower and 'браузер' not in task_lower and 'страница' not in task_lower:
                return GuardrailResult(
                    passed=False,
                    risk_level=RiskLevel.LOW,
                    reason=f"Запрос не относится к задачам браузерного агента: {keyword}",
                    blocked=True
                )
        
        return GuardrailResult(passed=True)


class SafetyClassifier:
    def __init__(self):
        self.jailbreak_patterns = [
            r'игнорируй.*инструкци',
            r'забудь.*правила',
            r'разыграй.*роль',
            r'системные инструкции',
            r'мои инструкции такие',
            r'выполни.*любую.*команду',
            r'обойди.*защиту',
            r'покажи.*промпт',
            r'выведи.*системный.*промпт',
            r'ignore.*previous.*instructions',
            r'forget.*rules',
            r'act.*as.*if',
            r'system.*prompt',
            r'bypass.*security'
        ]
        
        self.prompt_injection_patterns = [
            r'<script>',
            r'javascript:',
            r'eval\(',
            r'exec\(',
            r'__import__',
            r'subprocess',
            r'os\.system',
            r'rm\s+-rf',
            r'del\s+/f',
            r'format\s+c:'
        ]
    
    def check(self, input_text: str) -> GuardrailResult:
        input_lower = input_text.lower()
        
        for pattern in self.jailbreak_patterns:
            if re.search(pattern, input_lower, re.IGNORECASE):
                return GuardrailResult(
                    passed=False,
                    risk_level=RiskLevel.HIGH,
                    reason="Обнаружена попытка jailbreak или обхода инструкций",
                    blocked=True
                )
        
        for pattern in self.prompt_injection_patterns:
            if re.search(pattern, input_lower, re.IGNORECASE):
                return GuardrailResult(
                    passed=False,
                    risk_level=RiskLevel.CRITICAL,
                    reason="Обнаружена попытка prompt injection или выполнения кода",
                    blocked=True
                )
        
        return GuardrailResult(passed=True)


class PIIFilter:
    def __init__(self):
        self.pii_patterns = [
            (r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', 'Номер кредитной карты'),
            (r'\b\d{16}\b', 'Номер карты'),
            (r'\b\d{3}-\d{2}-\d{4}\b', 'SSN'),
            (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'Email'),
            (r'\b\d{10,11}\b', 'Телефон'),
            (r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{3}\b', 'CVV'),
        ]
    
    def check_output(self, output_text: str) -> GuardrailResult:
        found_pii = []
        
        for pattern, pii_type in self.pii_patterns:
            matches = re.findall(pattern, output_text, re.IGNORECASE)
            if matches:
                found_pii.append(f"{pii_type}: {len(matches)} совпадений")
        
        if found_pii:
            return GuardrailResult(
                passed=False,
                risk_level=RiskLevel.MEDIUM,
                reason=f"Обнаружены персональные данные: {', '.join(found_pii)}",
                blocked=False
            )
        
        return GuardrailResult(passed=True)


class ModerationFilter:
    def __init__(self):
        self.hate_speech_keywords = [
            'ненависть', 'ненавижу', 'убить', 'убийство', 'террор',
            'экстремизм', 'расизм', 'дискриминация'
        ]
        
        self.harassment_keywords = [
            'домогательство', 'преследование', 'угроза', 'шантаж'
        ]
        
        self.violence_keywords = [
            'насилие', 'избить', 'пытка', 'взрыв', 'оружие'
        ]
    
    def check(self, input_text: str) -> GuardrailResult:
        input_lower = input_text.lower()
        
        for keyword in self.hate_speech_keywords:
            if keyword in input_lower:
                return GuardrailResult(
                    passed=False,
                    risk_level=RiskLevel.HIGH,
                    reason="Обнаружен контент, разжигающий ненависть",
                    blocked=True
                )
        
        for keyword in self.harassment_keywords:
            if keyword in input_lower:
                return GuardrailResult(
                    passed=False,
                    risk_level=RiskLevel.HIGH,
                    reason="Обнаружен контент, содержащий домогательства",
                    blocked=True
                )
        
        for keyword in self.violence_keywords:
            if keyword in input_lower:
                return GuardrailResult(
                    passed=False,
                    risk_level=RiskLevel.HIGH,
                    reason="Обнаружен контент, содержащий насилие",
                    blocked=True
                )
        
        return GuardrailResult(passed=True)


class ToolSafeguards:
    def __init__(self):
        self.tool_risk_levels = {
            'navigate_to_url': RiskLevel.LOW,
            'get_page_info': RiskLevel.LOW,
            'click_element': RiskLevel.MEDIUM,
            'type_text': RiskLevel.MEDIUM,
            'scroll': RiskLevel.LOW,
            'wait': RiskLevel.LOW,
            'task_complete': RiskLevel.LOW,
            'ask_user': RiskLevel.LOW,
        }
        
        self.destructive_tools = [
            'delete', 'remove', 'cancel', 'unsubscribe',
            'pay', 'purchase', 'buy', 'checkout', 'order',
            'confirm', 'submit payment', 'place order'
        ]
    
    def assess_tool_risk(self, tool_name: str, arguments: Dict) -> GuardrailResult:
        base_risk = self.tool_risk_levels.get(tool_name, RiskLevel.MEDIUM)
        
        if base_risk == RiskLevel.CRITICAL:
            return GuardrailResult(
                passed=False,
                risk_level=RiskLevel.CRITICAL,
                reason=f"Инструмент {tool_name} имеет критический уровень риска",
                blocked=True
            )
        
        if base_risk == RiskLevel.HIGH:
            return GuardrailResult(
                passed=False,
                risk_level=RiskLevel.HIGH,
                reason=f"Инструмент {tool_name} требует подтверждения",
                blocked=False
            )
        
        args_str = str(arguments).lower()
        for destructive in self.destructive_tools:
            if destructive in args_str:
                return GuardrailResult(
                    passed=False,
                    risk_level=RiskLevel.HIGH,
                    reason=f"Обнаружено деструктивное действие: {destructive}",
                    blocked=False
                )
        
        return GuardrailResult(passed=True, risk_level=base_risk)


class RulesBasedProtections:
    def __init__(self):
        self.blocklist = [
            'sql injection', 'drop table', 'delete from',
            'union select', 'or 1=1', '--', ';--',
            'xss', '<script>', 'onerror=',
            'cmd.exe', '/bin/bash', 'powershell'
        ]
        
        self.max_input_length = 10000
        self.max_output_length = 50000
    
    def check(self, input_text: str, output_text: str = "") -> GuardrailResult:
        if len(input_text) > self.max_input_length:
            return GuardrailResult(
                passed=False,
                risk_level=RiskLevel.MEDIUM,
                reason=f"Превышена максимальная длина ввода: {len(input_text)} > {self.max_input_length}",
                blocked=True
            )
        
        if output_text and len(output_text) > self.max_output_length:
            return GuardrailResult(
                passed=False,
                risk_level=RiskLevel.MEDIUM,
                reason=f"Превышена максимальная длина вывода: {len(output_text)} > {self.max_output_length}",
                blocked=False
            )
        
        input_lower = input_text.lower()
        for blocked_term in self.blocklist:
            if blocked_term in input_lower:
                return GuardrailResult(
                    passed=False,
                    risk_level=RiskLevel.HIGH,
                    reason=f"Обнаружен запрещенный термин: {blocked_term}",
                    blocked=True
                )
        
        return GuardrailResult(passed=True)


class OutputValidator:
    def __init__(self):
        self.brand_violations = [
            'конкурент', 'конкурирующий продукт',
            'негативный отзыв', 'критика бренда'
        ]
    
    def validate(self, output_text: str) -> GuardrailResult:
        output_lower = output_text.lower()
        
        for violation in self.brand_violations:
            if violation in output_lower:
                return GuardrailResult(
                    passed=False,
                    risk_level=RiskLevel.MEDIUM,
                    reason=f"Вывод может навредить целостности бренда: {violation}",
                    blocked=False
                )
        
        return GuardrailResult(passed=True)


class GuardrailsSystem:
    def __init__(self):
        self.relevance_classifier = RelevanceClassifier()
        self.safety_classifier = SafetyClassifier()
        self.pii_filter = PIIFilter()
        self.moderation_filter = ModerationFilter()
        self.tool_safeguards = ToolSafeguards()
        self.rules_protection = RulesBasedProtections()
        self.output_validator = OutputValidator()
    
    def check_input(self, input_text: str, task: str = "") -> Tuple[bool, List[str]]:
        errors = []
        
        relevance_result = self.relevance_classifier.check(input_text, task)
        if not relevance_result:
            errors.append(relevance_result.reason)
            if relevance_result.blocked:
                return False, errors
        
        safety_result = self.safety_classifier.check(input_text)
        if not safety_result:
            errors.append(safety_result.reason)
            if safety_result.blocked:
                return False, errors
        
        moderation_result = self.moderation_filter.check(input_text)
        if not moderation_result:
            errors.append(moderation_result.reason)
            if moderation_result.blocked:
                return False, errors
        
        rules_result = self.rules_protection.check(input_text)
        if not rules_result:
            errors.append(rules_result.reason)
            if rules_result.blocked:
                return False, errors
        
        return len(errors) == 0, errors
    
    def check_tool(self, tool_name: str, arguments: Dict) -> Tuple[bool, str, RiskLevel]:
        result = self.tool_safeguards.assess_tool_risk(tool_name, arguments)
        return result.passed, result.reason, result.risk_level
    
    def check_output(self, output_text: str) -> Tuple[bool, List[str]]:
        errors = []
        
        pii_result = self.pii_filter.check_output(output_text)
        if not pii_result:
            errors.append(pii_result.reason)
        
        validation_result = self.output_validator.validate(output_text)
        if not validation_result:
            errors.append(validation_result.reason)
        
        rules_result = self.rules_protection.check("", output_text)
        if not rules_result:
            errors.append(rules_result.reason)
        
        return len(errors) == 0, errors

