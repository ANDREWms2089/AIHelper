from typing import List, Dict


class ContextManager:
    def __init__(self, max_context_length: int = 10000):
        self.max_context_length = max_context_length
        self.history: List[Dict] = []
        self.current_page_info = None
    
    def update_page_info(self, page_summary: dict):
        self.current_page_info = page_summary

