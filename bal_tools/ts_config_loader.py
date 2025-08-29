import json
import re
import urllib.request
from pathlib import Path
from typing import Dict, Any, Union


def ts_config_loader(src: Union[str, Path]) -> Dict[str, Any]:
    """
    Turn a Balancer network-config TypeScript file into a Python dict.

    src  – local path or https://… URL
    """
    raw = _read(src)
    literal = _extract_object_literal(raw)
    json_text = _to_json(literal)
    return json.loads(json_text)


# ────────────────────────── helpers ──────────────────────────
def _read(src: Union[str, Path]) -> str:
    if str(src).startswith(("http://", "https://")):
        with urllib.request.urlopen(str(src), timeout=20) as fp:
            return fp.read().decode()
    return Path(src).read_text(encoding="utf-8")


def _extract_object_literal(ts: str) -> str:
    # drop every line starting with "import "
    ts = "\n".join(l for l in ts.splitlines() if not l.lstrip().startswith("import "))
    # keep everything starting at "export default"
    start = ts.index("export default") + len("export default")
    chunk = ts[start:]

    # find matching braces
    open_idx = chunk.index("{")
    depth = 0
    for idx, ch in enumerate(chunk[open_idx:], open_idx):
        depth += +1 if ch == "{" else -1 if ch == "}" else 0
        if depth == 0:
            close_idx = idx
            break
    return chunk[open_idx : close_idx + 1]


def _to_json(obj: str) -> str:
    # 1) Convert backtick strings to double-quoted strings FIRST
    # (before comment removal to avoid issues with URLs containing //)
    # This handles template literals like `string with ${variable}`
    def convert_backtick(match):
        content = match.group(1)
        # Only escape double quotes that aren't already escaped
        content = content.replace('"', '\\"')
        return f'"{content}"'

    obj = re.sub(r"`([^`]*)`", convert_backtick, obj, flags=re.DOTALL)
    
    # 1b) Handle arrow functions by converting them to null
    # This handles parser functions like (data: any) => Number(data[5]) / 1e27
    # First handle simple arrow functions (but not those that are part of .map())
    # Negative lookbehind to avoid matching .map( arrow functions
    obj = re.sub(r'(?<!\.map)\([^)]*\)\s*=>\s*[^,\n]+', 'null', obj)
    
    # Handle arrow functions with type annotations like (token: any): [string, number] => [...]
    # These are more complex and can span multiple lines
    def replace_arrow_functions(text):
        # Look for patterns like "(param: type): returnType => "
        pattern = r'\([^)]*\)\s*:\s*[^=]*=>\s*'
        matches = list(re.finditer(pattern, text))
        
        # Process from end to start to maintain indices
        for match in reversed(matches):
            start = match.start()
            # Find the end of the arrow function body
            # It ends at a comma or closing brace/bracket at the same level
            i = match.end()
            depth = 0
            in_string = False
            string_char = None
            
            while i < len(text):
                if not in_string:
                    if text[i] in '"\'':
                        in_string = True
                        string_char = text[i]
                    elif text[i] in '[{(':
                        depth += 1
                    elif text[i] in ']})':
                        depth -= 1
                        if depth < 0:
                            # Found the end
                            break
                    elif text[i] == ',' and depth == 0:
                        # Found the end
                        break
                else:
                    if text[i] == string_char and (i == 0 or text[i-1] != '\\\\'):
                        in_string = False
                i += 1
            
            # Replace the arrow function with null
            text = text[:start] + 'null' + text[i:]
        
        return text
    
    obj = replace_arrow_functions(obj)
    
    # 1c) Handle $.xxx patterns (JSONPath expressions) by quoting them
    # This handles path values like $.apy or $.data
    obj = re.sub(r'(\$\.[a-zA-Z0-9_.]+)', r'"\1"', obj)
    
    # 1c2) Handle spread operator with arrays and potential .map() calls
    # More robust handling of ...[array].map() patterns
    def handle_spread_with_map(text):
        # Find patterns like ...[...].map(...)
        pattern = r'\.\.\.\s*\[[^\]]*\]\.map\s*\([^)]*\)\s*=>\s*\({'
        match = re.search(pattern, text)
        
        if match:
            # Find the start of the spread operator
            start = match.start()
            # Find the end of the map function - need to find matching }))
            i = match.end() - 1  # Position at the { after =>
            brace_count = 1
            
            while i < len(text) and brace_count > 0:
                i += 1
                if i < len(text):
                    if text[i] == '{':
                        brace_count += 1
                    elif text[i] == '}':
                        brace_count -= 1
            
            # Now skip the closing ))
            while i < len(text) and text[i] in ') \n':
                i += 1
            
            # Replace the entire spread...map expression with an empty array
            text = text[:start] + '[]' + text[i:]
            # Recursively handle any remaining patterns
            return handle_spread_with_map(text)
        
        return text
    
    obj = handle_spread_with_map(obj)
    
    # Then handle simple spread operators: ...[array] -> [array]
    obj = re.sub(r'\.\.\.\s*\[', '[', obj)
    
    # 1d) Handle JSON.stringify() calls with nested content
    # Find JSON.stringify and match its balanced parentheses
    def replace_json_stringify(text):
        while 'JSON.stringify(' in text:
            start = text.find('JSON.stringify(')
            if start == -1:
                break
            
            # Find the matching closing parenthesis
            open_count = 0
            i = start + len('JSON.stringify(')
            while i < len(text):
                if text[i] == '(':
                    open_count += 1
                elif text[i] == ')':
                    if open_count == 0:
                        # Found the matching closing parenthesis
                        text = text[:start] + 'null' + text[i+1:]
                        break
                    open_count -= 1
                i += 1
            else:
                # If we couldn't find a matching paren, just replace with null
                text = text[:start] + 'null' + text[start+15:]
        return text
    
    obj = replace_json_stringify(obj)

    # 2) Strip comments (after backtick conversion to avoid URL issues)
    obj = re.sub(r"/\*[\s\S]*?\*/", "", obj)
    # Remove // comments - both line-start and inline, but avoid URLs
    # First remove line-start comments
    obj = re.sub(r"^\s*//.*", "", obj, flags=re.MULTILINE)
    # Then remove inline comments that are clearly not URLs (preceded by space, ], }, or ,)
    obj = re.sub(r"([\s\]\},])\s*//.*", r"\1", obj)

    # 3) Convert single-quoted strings to double-quoted strings
    def convert_single_quote(match):
        content = match.group(1)
        # Handle escaped single quotes and escape double quotes
        content = content.replace("\\'", "'")  # unescape single quotes
        content = content.replace('"', '\\"')  # escape double quotes
        return f'"{content}"'

    obj = re.sub(r"'([^'\\]*(?:\\.[^'\\]*)*)'", convert_single_quote, obj)

    # 4) Quote unquoted object keys - be more careful about context
    # Only match keys that are at the start of a line (after whitespace) or after { or ,
    obj = re.sub(
        r"(^|\s*[{,]\s*)([a-zA-Z_$][a-zA-Z0-9_$]*)\s*:",
        r'\1"\2":',
        obj,
        flags=re.MULTILINE,
    )

    # 5) Handle bracket notation keys like ['0x123']: -> "0x123":
    # First handle quoted bracket notation: ['key'] -> "key"
    obj = re.sub(r"\['([^']+)'\]\s*:", r'"\1":', obj)
    # Then handle double-quoted bracket notation: ["key"] -> "key"
    obj = re.sub(r'\["([^"]+)"\]\s*:', r'"\1":', obj)
    # Finally handle unquoted bracket notation: [key] -> "key"
    obj = re.sub(r"\[([^\]'\"]+)\]\s*:", r'"\1":', obj)

    # 6) Handle BigNumber constructs: BigNumber.from("123") -> "123"
    obj = re.sub(r"BigNumber\.from\(([^)]+)\)", r"\1", obj)

    # 6b) Handle object property references: object.property -> "object.property"
    # This handles cases like underlyingTokens.USDC
    obj = re.sub(
        r":\s*([a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*),", r': "\1",', obj
    )

    # 7) Handle specific ternary expressions that are common in config files
    # Replace the rpcUrl ternary with the fallback value for simplicity
    obj = re.sub(
        r'"rpcUrl":\s*env\.DRPC_API_KEY\s*\?\s*"[^"]+"\s*:\s*([^,]+),',
        r'"rpcUrl": \1,',
        obj,
        flags=re.MULTILINE | re.DOTALL,
    )

    # 8) remove trailing commas
    obj = re.sub(r",\s*(?=[}\]])", "", obj)

    return obj
