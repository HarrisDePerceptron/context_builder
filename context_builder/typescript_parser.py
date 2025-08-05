#!/usr/bin/env python3
"""
TypeScript parser for context builder
Uses regex-based parsing to extract function signatures, class definitions, and types from TypeScript files.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

class TypeScriptParser:
    """Parser for TypeScript files using regex-based parsing."""
    
    def parse_file(self, file_path: Path) -> Tuple[List[str], List[str]]:
        """
        Parse a TypeScript file and return function signatures and class definitions.
        
        Returns:
            Tuple of (function_lines, class_lines)
        """
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            return self._parse_with_regex(content, file_path)
        except Exception:
            return [], []
    
    def _parse_with_regex(self, content: str, file_path: Path) -> Tuple[List[str], List[str]]:
        """Fallback regex-based parsing for TypeScript."""
        func_lines: List[str] = []
        cls_lines: List[str] = []
        rel_path = file_path.name
        
        # Function patterns
        function_patterns = [
            # Regular functions
            r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)(?:\s*:\s*([^{]+))?',
            # Arrow functions assigned to variables
            r'(?:export\s+)?(?:const|let|var)\s+(\w+)\s*[:=]\s*(?:async\s+)?\(([^)]*)\)(?:\s*=>\s*[^{]+)?',
            # Method definitions in classes/interfaces
            r'(\w+)\s*\(([^)]*)\)(?:\s*:\s*([^{]+))?',
        ]
        
        # Class patterns
        class_patterns = [
            r'(?:export\s+)?(?:abstract\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([^{]+))?',
            r'(?:export\s+)?interface\s+(\w+)(?:\s+extends\s+([^{]+))?',
            r'(?:export\s+)?type\s+(\w+)\s*=\s*([^;]+)',
        ]
        
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # Check for functions
            for pattern in function_patterns:
                match = re.search(pattern, line)
                if match:
                    func_name = match.group(1)
                    params = match.group(2).strip()
                    return_type = match.group(3).strip() if len(match.groups()) > 2 and match.group(3) else "any"
                    
                    # Clean up parameters
                    if params:
                        params = self._clean_typescript_params(params)
                    
                    func_lines.append(f"{rel_path}:{i}: {func_name}({params}) -> {return_type}")
                    break
            
            # Check for classes/interfaces
            for pattern in class_patterns:
                match = re.search(pattern, line)
                if match:
                    class_name = match.group(1)
                    extends = match.group(2) if len(match.groups()) > 1 and match.group(2) else ""
                    implements = match.group(3) if len(match.groups()) > 2 and match.group(3) else ""
                    
                    class_def = f"class {class_name}"
                    if extends:
                        class_def += f" extends {extends}"
                    if implements:
                        class_def += f" implements {implements}"
                    
                    cls_lines.append(f"{rel_path}:{i}: {class_def}")
                    break
        
        return func_lines, cls_lines
    
    def _clean_typescript_params(self, params: str) -> str:
        """Clean and format TypeScript parameters."""
        if not params:
            return ""
        
        # Split by comma, but be careful about nested parentheses
        param_list = []
        current_param = ""
        paren_count = 0
        
        for char in params:
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
            elif char == ',' and paren_count == 0:
                param_list.append(current_param.strip())
                current_param = ""
                continue
            current_param += char
        
        if current_param.strip():
            param_list.append(current_param.strip())
        
        # Clean up each parameter
        cleaned_params = []
        for param in param_list:
            # Remove default values
            if '=' in param:
                param = param.split('=')[0].strip()
            
            # Clean up type annotations
            if ':' in param:
                name, type_ann = param.split(':', 1)
                name = name.strip()
                type_ann = type_ann.strip()
                cleaned_params.append(f"{name}: {type_ann}")
            else:
                cleaned_params.append(param.strip())
        
        return ", ".join(cleaned_params)
    
# Global parser instance
ts_parser = TypeScriptParser() 