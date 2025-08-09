"""
AST (Abstract Syntax Tree) Analyzer for Python Code

Provides static analysis capabilities using Python's AST module.
"""

import ast
import sys
from typing import Dict, List, Any, Set, Tuple
from collections import defaultdict

class ASTAnalyzer(ast.NodeVisitor):
    """Analyzes Python code using Abstract Syntax Tree parsing"""
    
    def __init__(self):
        self.functions = []
        self.classes = []
        self.imports = []
        self.global_vars = []
        self.function_calls = defaultdict(int)
        self.complexity_scores = {}
        self.security_patterns = []
        self.code_smells = []
        self.current_function = None
        self.current_class = None
        
    def analyze(self, code: str) -> Dict[str, Any]:
        """Analyze Python code and extract metrics
        
        Args:
            code: Python source code as string
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            tree = ast.parse(code)
            self.visit(tree)
            
            return {
                "ast_analysis": {
                    "functions": self.functions,
                    "classes": self.classes,
                    "imports": self.imports,
                    "global_variables": self.global_vars,
                    "function_calls": dict(self.function_calls),
                    "complexity": self.complexity_scores,
                    "metrics": self._calculate_metrics(),
                    "security_patterns": self.security_patterns,
                    "code_smells": self.code_smells
                }
            }
        except SyntaxError as e:
            return {
                "ast_analysis": {
                    "error": f"Syntax error: {str(e)}",
                    "line": e.lineno,
                    "offset": e.offset
                }
            }
        except Exception as e:
            return {
                "ast_analysis": {
                    "error": f"AST analysis failed: {str(e)}"
                }
            }
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Analyze function definitions"""
        self.current_function = node.name
        
        # Calculate cyclomatic complexity
        complexity = self._calculate_cyclomatic_complexity(node)
        self.complexity_scores[node.name] = complexity
        
        # Check for code smells
        if len(node.args.args) > 5:
            self.code_smells.append({
                "type": "too_many_parameters",
                "function": node.name,
                "line": node.lineno,
                "parameter_count": len(node.args.args)
            })
        
        # Check function length
        function_lines = node.end_lineno - node.lineno
        if function_lines > 50:
            self.code_smells.append({
                "type": "long_function",
                "function": node.name,
                "line": node.lineno,
                "lines": function_lines
            })
        
        # Store function info
        self.functions.append({
            "name": node.name,
            "line": node.lineno,
            "parameters": [arg.arg for arg in node.args.args],
            "complexity": complexity,
            "decorators": [self._get_decorator_name(d) for d in node.decorator_list],
            "is_async": isinstance(node, ast.AsyncFunctionDef),
            "docstring": ast.get_docstring(node) is not None
        })
        
        self.generic_visit(node)
        self.current_function = None
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Handle async functions"""
        self.visit_FunctionDef(node)
    
    def visit_ClassDef(self, node: ast.ClassDef):
        """Analyze class definitions"""
        self.current_class = node.name
        
        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(item.name)
        
        self.classes.append({
            "name": node.name,
            "line": node.lineno,
            "methods": methods,
            "bases": [self._get_name(base) for base in node.bases],
            "decorators": [self._get_decorator_name(d) for d in node.decorator_list],
            "docstring": ast.get_docstring(node) is not None
        })
        
        self.generic_visit(node)
        self.current_class = None
    
    def visit_Import(self, node: ast.Import):
        """Track imports"""
        for alias in node.names:
            self.imports.append({
                "module": alias.name,
                "alias": alias.asname,
                "line": node.lineno,
                "type": "import"
            })
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Track from imports"""
        module = node.module or ""
        for alias in node.names:
            self.imports.append({
                "module": module,
                "name": alias.name,
                "alias": alias.asname,
                "line": node.lineno,
                "type": "from_import"
            })
        self.generic_visit(node)
    
    def visit_Call(self, node: ast.Call):
        """Track function calls and detect security patterns"""
        func_name = self._get_call_name(node)
        if func_name:
            self.function_calls[func_name] += 1
            
            # Check for dangerous functions
            dangerous_functions = {
                "eval": "Code injection risk",
                "exec": "Code injection risk",
                "compile": "Code injection risk",
                "__import__": "Dynamic import risk",
                "pickle.loads": "Deserialization vulnerability",
                "yaml.load": "Unsafe YAML loading",
                "subprocess.call": "Command injection risk",
                "os.system": "Command injection risk"
            }
            
            if func_name in dangerous_functions:
                self.security_patterns.append({
                    "type": "dangerous_function",
                    "function": func_name,
                    "line": node.lineno,
                    "risk": dangerous_functions[func_name]
                })
        
        self.generic_visit(node)
    
    def visit_Assign(self, node: ast.Assign):
        """Track global variables and hardcoded secrets"""
        # Check for global variables
        if self.current_function is None and self.current_class is None:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.global_vars.append({
                        "name": target.id,
                        "line": node.lineno
                    })
        
        # Check for hardcoded secrets
        if isinstance(node.value, ast.Constant):
            value_str = str(node.value.value).lower()
            for target in node.targets:
                if isinstance(target, ast.Name):
                    var_name = target.id.lower()
                    if any(secret in var_name for secret in ["password", "secret", "key", "token", "api"]):
                        if isinstance(node.value.value, str) and len(node.value.value) > 0:
                            self.security_patterns.append({
                                "type": "hardcoded_secret",
                                "variable": target.id,
                                "line": node.lineno
                            })
        
        self.generic_visit(node)
    
    def visit_Try(self, node: ast.Try):
        """Check exception handling"""
        # Check for bare except
        for handler in node.handlers:
            if handler.type is None:
                self.code_smells.append({
                    "type": "bare_except",
                    "line": handler.lineno,
                    "function": self.current_function
                })
            # Check for except Exception (too broad)
            elif isinstance(handler.type, ast.Name) and handler.type.id == "Exception":
                self.code_smells.append({
                    "type": "broad_exception",
                    "line": handler.lineno,
                    "function": self.current_function
                })
        
        self.generic_visit(node)
    
    def _calculate_cyclomatic_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity of a function"""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            # Each decision point adds 1 to complexity
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                # Each and/or adds complexity
                complexity += len(child.values) - 1
            elif isinstance(child, ast.Try):
                # Each except clause adds complexity
                complexity += len(child.handlers)
        
        return complexity
    
    def _calculate_metrics(self) -> Dict[str, Any]:
        """Calculate code metrics"""
        total_complexity = sum(self.complexity_scores.values()) if self.complexity_scores else 0
        avg_complexity = total_complexity / len(self.complexity_scores) if self.complexity_scores else 0
        
        return {
            "total_functions": len(self.functions),
            "total_classes": len(self.classes),
            "total_imports": len(self.imports),
            "global_variables": len(self.global_vars),
            "avg_complexity": round(avg_complexity, 2),
            "max_complexity": max(self.complexity_scores.values()) if self.complexity_scores else 0,
            "high_complexity_functions": [
                func for func, score in self.complexity_scores.items() if score > 10
            ],
            "security_issues": len(self.security_patterns),
            "code_smell_count": len(self.code_smells)
        }
    
    def _get_name(self, node) -> str:
        """Extract name from various node types"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return "unknown"
    
    def _get_call_name(self, node: ast.Call) -> str:
        """Extract function name from call node"""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return f"{self._get_name(node.func.value)}.{node.func.attr}"
        return ""
    
    def _get_decorator_name(self, node) -> str:
        """Extract decorator name"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Call):
            return self._get_call_name(node)
        return "unknown"


def analyze_python_code(code: str) -> Dict[str, Any]:
    """Convenience function to analyze Python code"""
    analyzer = ASTAnalyzer()
    return analyzer.analyze(code)