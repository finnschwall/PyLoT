import inspect
from docstring_parser import parse
import ast


def generate_python_doc(func_name, func_dict):
    args = func_dict.get('args', [])
    kwargs = func_dict.get('kwargs', [])
    doc = f"def {func_name}("
    for arg in args:
        arg_type = ""
        if "type" in arg:
            arg_type = ":" + arg["type"]
        doc += f"{arg['name']}" + arg_type + ", "
    for kwarg in kwargs:
        kwarg_type = ""
        if "type" in kwarg:
            kwarg_type = ":" + kwarg["type"]
        doc += f"{kwarg['name']}{kwarg_type}={kwarg.get('default', 'None')}, "
    doc = doc.rstrip(', ') + ")\n"
    doc += '"""\n'
    if "description" in func_dict:
        doc += func_dict["description"] + "\n"
    for arg in args:
        if "description" in arg:
            doc += f":param {arg['name']}: {arg.get('description', '')}\n"
    for kwarg in kwargs:
        doc += f":param {kwarg['name']}: {kwarg.get('description', '')}\n"
    if "return" in func_dict:
        doc += ":return: " + func_dict["return"]
    doc += '"""'
    return doc


def function_signature_to_dict(func):
    sig = inspect.signature(func)
    params = sig.parameters

    doc = parse(func.__doc__)

    args = []
    kwargs = []
    has_var_positional = False  # Flag for *args
    has_var_keyword = False  # Flag for **kwargs

    for name, param in params.items():
        if param.kind == inspect.Parameter.VAR_POSITIONAL:
            has_var_positional = True
        elif param.kind == inspect.Parameter.VAR_KEYWORD:
            has_var_keyword = True
        elif param.default == inspect.Parameter.empty:
            arg = {'name': name}
            for doc_param in doc.params:
                if doc_param.arg_name == name:
                    if doc_param.type_name:
                        arg['type'] = doc_param.type_name
                    if doc_param.description and doc_param.description != "":
                        arg['description'] = doc_param.description
            args.append(arg)
        else:
            kwarg = {'name': name, 'default': param.default}
            for doc_param in doc.params:
                if doc_param.arg_name == name:
                    kwarg_type = doc_param.type_name
                    if not kwarg_type:
                        if param.default:
                            kwarg_type = type(param.default).__name__
                    if kwarg_type:
                        kwarg['type'] = kwarg_type
                    if doc_param.description and doc_param.description != "":
                        kwarg['description'] = doc_param.description
            kwargs.append(kwarg)

    return {
        'name': func.__name__,
        'description': doc.short_description,
        'args': args,
        'kwargs': kwargs,
        'has_var_positional': has_var_positional,
        'has_var_keyword': has_var_keyword
    }



class CodeVisitor(ast.NodeVisitor):
    def __init__(self, func_map={}, collect=False):
        self.func_map = func_map
        self.collect = collect
        self.variables = {}
        self.collection = []

    def visit_Call(self, node):
        func_name = node.func.id
        args = [self.variables.get(arg.id, None) if isinstance(arg, ast.Name) else ast.literal_eval(arg) for arg in
                node.args]
        kwargs = {kw.arg: self.variables.get(kw.value.id, None) if isinstance(kw.value, ast.Name) else ast.literal_eval(
            kw.value) for kw in node.keywords}

        # print(f'Function call: {func_name}({args}, {kwargs})')
        resolved_func = self.func_map.get(func_name)
        if resolved_func:
            result = resolved_func(*args, **kwargs)
            self.variables['__call_res__'] = result
            return result
        elif self.collect:
            self.collection.append({"name": func_name, "args": args, "kwargs": kwargs})
            # self.variables['__call_res__'] = "INSERT_LATER"
        else:
            return f"Function {func_name} not found"

    def visit_Assign(self, node):
        if isinstance(node.targets[0], ast.Name):
            var_name = node.targets[0].id
            if isinstance(node.value, ast.Call):
                value = self.visit(node.value)
            elif isinstance(node.value, ast.Name):
                value = self.variables.get(node.value.id)
            else:
                value = ast.literal_eval(node.value)

            self.variables[var_name] = value
            # print(f'Variable assignment: {var_name} = {value}')
