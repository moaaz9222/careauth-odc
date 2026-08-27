import json
import re

def repair_json(raw: str) -> str:
    """
    Attempts to repair malformed JSON from LLM responses.
    Try common fixes: strip markdown code fences, fix trailing commas, fix missing quotes, balance brackets
    Returns valid JSON string or raises ValueError
    """
    s = raw.strip()
    
    # Strip markdown code fences
    if s.startswith("```"):
        # find the end of the first line
        first_line_end = s.find("\n")
        if first_line_end != -1:
            s = s[first_line_end+1:]
        if s.endswith("```"):
            s = s[:-3]
    s = s.strip()

    # Try to parse immediately
    try:
        json.loads(s)
        return s
    except json.JSONDecodeError:
        pass

    # Fix trailing commas
    s = re.sub(r',\s*([\]}])', r'\1', s)
    
    # Add missing brackets? It's a simple fix. We'll just count them.
    open_braces = s.count('{')
    close_braces = s.count('}')
    open_brackets = s.count('[')
    close_brackets = s.count(']')
    
    if open_braces > close_braces:
        s += '}' * (open_braces - close_braces)
    if open_brackets > close_brackets:
        s += ']' * (open_brackets - close_brackets)

    try:
        json.loads(s)
        return s
    except json.JSONDecodeError as e:
        raise ValueError(f"Could not repair JSON: {e}")
