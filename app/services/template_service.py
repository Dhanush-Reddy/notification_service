import re

# matches {{variable_name}} per spec — not Jinja2, not f-strings
_TEMPLATE_PATTERN = re.compile(r"\{\{(\w+)\}\}")


def render(body: str, variables: dict) -> str:
    """Replace {{key}} placeholders with values from variables dict.
    Unknown keys are left as-is rather than raising an error.
    """
    def sub(match: re.Match) -> str:
        key = match.group(1).strip()
        return str(variables.get(key, match.group(0)))

    return _TEMPLATE_PATTERN.sub(sub, body)
