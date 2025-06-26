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
