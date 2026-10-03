"""Small exact tools: a calculator, unit conversion and date/time questions.

Everything is rules and arithmetic — no look-up, no guessing. Each detector returns ``None``
when the message is not for it, so the router can try them cheaply on every sentence.

* calculator: + − × ÷, powers, roots, percentages, parentheses, number words ("five times
  three"), "15% of 80"; evaluated on a whitelisted syntax tree, never with ``eval``;
* units: length, mass, volume, area, speed, time, data and temperature ("5 miles in km");
* dates: today's date, weekday, time, year, "what day is 24 December 2026", "how many days
  until Christmas".
"""

from __future__ import annotations

import ast
import datetime as dt
import math
import operator
import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# numbers
# ---------------------------------------------------------------------------

_SMALL = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
          "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
          "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
          "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90, "a": 1, "an": 1}
_SCALE = {"hundred": 100, "thousand": 1_000, "million": 1_000_000, "billion": 1_000_000_000,
          "trillion": 1_000_000_000_000}
_NUMWORD = re.compile(r"\b(?:(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|"
                      r"fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|"
                      r"seventy|eighty|ninety|hundred|thousand|million|billion|trillion)(?:[\s-]+(?:and[\s-]+)?|\b))+",
                      re.I)


def words_to_number(text: str) -> int | None:
    total, current = 0, 0
    parts = [p for p in re.split(r"[\s-]+", text.lower().strip()) if p and p != "and"]
    if not parts:
        return None
    for p in parts:
        if p in _SMALL:
            current += _SMALL[p]
        elif p == "hundred":
            current = max(current, 1) * 100
        elif p in _SCALE:
            total += max(current, 1) * _SCALE[p]
            current = 0
        else:
            return None
    return total + current


def _replace_number_words(s: str) -> str:
    def rep(m):
        n = words_to_number(m.group(0))
        return f" {n} " if n is not None else m.group(0)
    return _NUMWORD.sub(rep, s)


def fmt_number(x: float) -> str:
    """12 → "12", 3.5 → "3.5", 0.333… → "0.3333", 1234567 → "1,234,567", huge → 1.23e+20."""
    if isinstance(x, bool):
        x = int(x)
    if isinstance(x, int) or (isinstance(x, float) and x.is_integer() and abs(x) < 1e15):
        return f"{int(x):,}"
    if not math.isfinite(x):
        return "infinity" if x > 0 else ("minus infinity" if x < 0 else "undefined")
    if abs(x) >= 1e15 or (abs(x) < 1e-4 and x != 0):
        return f"{x:.4g}"
    s = f"{x:,.6f}".rstrip("0").rstrip(".")
    return s if s not in ("-0", "") else "0"


# ---------------------------------------------------------------------------
# calculator
# ---------------------------------------------------------------------------

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Mod: operator.mod, ast.FloorDiv: operator.floordiv, ast.Pow: operator.pow}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCS = {"sqrt": math.sqrt, "cbrt": lambda x: math.copysign(abs(x) ** (1 / 3), x), "abs": abs, "log": math.log10,
          "ln": math.log, "sin": lambda x: math.sin(math.radians(x)), "cos": lambda x: math.cos(math.radians(x)),
          "tan": lambda x: math.tan(math.radians(x)), "round": round, "factorial": math.factorial,
          "exp": math.exp}
_CONST = {"pi": math.pi, "e": math.e}


class CalcError(ValueError):
    pass


def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        a, b = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow):
            if abs(b) > 1000 or (abs(a) > 1 and abs(b) * math.log10(abs(a) + 1) > 300):
                raise CalcError("that number is too large")
        if isinstance(node.op, (ast.Div, ast.Mod, ast.FloorDiv)) and b == 0:
            raise CalcError("you can't divide by zero")
        return _OPS[type(node.op)](a, b)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCS \
            and len(node.args) == 1 and not node.keywords:
        arg = _eval(node.args[0])
        if node.func.id == "factorial":
            if arg != int(arg) or arg < 0 or arg > 170:
                raise CalcError("factorials only for whole numbers from 0 to 170")
            arg = int(arg)
        if node.func.id in ("sqrt", "log", "ln") and arg < 0:
            raise CalcError("that's not defined for negative numbers")
        if node.func.id in ("log", "ln") and arg == 0:
            raise CalcError("the logarithm of zero is not defined")
        return _FUNCS[node.func.id](arg)
    if isinstance(node, ast.Name) and node.id in _CONST:
        return _CONST[node.id]
    raise CalcError("I can only do arithmetic")


_CALC_PREFIX = re.compile(r"^(?:(?:can you |could you |please )*(?:what(?:'s| is)|whats|calculate|compute|"
                          r"work out|evaluate|how much is|how much are|what does|solve|tell me|find)\s+)?", re.I)
_WORD_OPS = [
    (r"\bto the power of\b|\braised to(?: the power of)?\b|\^", " ** "),
    (r"\bsquare root of\b", " sqrt "), (r"\bcube root of\b", " cbrt "), (r"\bthe\b", " "),
    (r"\b(?:multiplied by|times|x|×|\*)\b", " * "), (r"×", " * "), (r"\bdivided by\b|\bover\b|÷", " / "),
    (r"\bplus\b|\band\b", " + "), (r"\bminus\b|\bless\b|−|–", " - "),
    (r"\bsquared\b", " ** 2 "), (r"\bcubed\b", " ** 3 "), (r"\bmod(?:ulo)?\b", " % "),
    (r"\bfactorial of\b", " factorial "),
]
_PERCENT_OF = re.compile(r"(-?\d+(?:\.\d+)?)\s*(?:%|percent|per cent)\s+of\s+(-?\d+(?:\.\d+)?)", re.I)
_EXPR_OK = re.compile(r"^[\d\s.+\-*/%()a-z,]*$")


@dataclass
class ToolResult:
    kind: str             # calc | units | date
    text: str             # the reply
    value: str | None = None


def calculate(message: str) -> ToolResult | None:
    """A reply for an arithmetic question, or None if the message is not one."""
    s = message.strip().rstrip("?.! =").strip()
    body = _CALC_PREFIX.sub("", s, count=1).strip()
    if not re.search(r"\d", body) and not _NUMWORD.search(body):
        return None
    low = body.lower().replace(",", "") if re.search(r"\d,\d{3}", body) else body.lower()
    low = _replace_number_words(low)
    m = _PERCENT_OF.search(low)
    if m and _PERCENT_OF.sub("", low).strip() == "":
        a, b = float(m.group(1)), float(m.group(2))
        val = a / 100 * b
        return ToolResult("calc", f"{fmt_number(a)}% of {fmt_number(b)} is {fmt_number(val)}.", fmt_number(val))
    expr = low
    for pat, rep in _WORD_OPS:
        expr = re.sub(pat, rep, expr)
    expr = re.sub(r"\s+", " ", expr).strip()
    if not expr or not _EXPR_OK.match(expr):
        return None
    names = set(re.findall(r"[a-z_]+", expr))
    if names - set(_FUNCS) - set(_CONST):
        return None
    if not re.search(r"[+\-*/]|%\s*\(?\d|\b(?:" + "|".join(_FUNCS) + r")\b", expr):
        return None                     # a bare number (or percentage) is not a calculation
    expr = re.sub(r"(\d+(?:\.\d+)?)\s*%(?!\s*\(?\d)", r"(\1/100)", expr)
    expr = re.sub(r"\b(" + "|".join(_FUNCS) + r")\s+(-?\d+(?:\.\d+)?|\([^()]*\))", r"\1(\2)", expr)
    try:
        tree = ast.parse(expr, mode="eval")
        val = _eval(tree)
    except CalcError as e:
        return ToolResult("calc", f"Hmm — {e}.")
    except (SyntaxError, TypeError, ValueError, OverflowError, ZeroDivisionError, RecursionError):
        return None
    shown = (expr.replace("**", "^").replace("*", "×").replace("/", "÷")
             .replace("sqrt(", "√(").replace(" ", " "))
    shown = re.sub(r"\s+", " ", shown).strip()
    return ToolResult("calc", f"{shown} = {fmt_number(val)}", fmt_number(val))


# ---------------------------------------------------------------------------
# units
# ---------------------------------------------------------------------------

# unit → (dimension, factor to the base unit); base: metre, kilogram, litre, square metre,
# metre per second, second, byte
_UNITS: dict[str, tuple[str, float]] = {}


def _add(dim: str, factor: float, *names: str) -> None:
    for n in names:
        _UNITS[n] = (dim, factor)


_add("length", 1.0, "m", "meter", "meters", "metre", "metres")
_add("length", 1000.0, "km", "kilometer", "kilometers", "kilometre", "kilometres", "kms")
_add("length", 0.01, "cm", "centimeter", "centimeters", "centimetre", "centimetres")
_add("length", 0.001, "mm", "millimeter", "millimeters", "millimetre", "millimetres")
_add("length", 1e-6, "micrometer", "micrometers", "micrometre", "micrometres", "micron", "microns")
_add("length", 1e-9, "nm", "nanometer", "nanometers", "nanometre", "nanometres")
_add("length", 0.0254, "in", "inch", "inches", "\"")
_add("length", 0.3048, "ft", "foot", "feet", "'")
_add("length", 0.9144, "yd", "yard", "yards")
_add("length", 1609.344, "mi", "mile", "miles")
_add("length", 1852.0, "nautical mile", "nautical miles", "nmi")
_add("length", 9.4607304725808e15, "light year", "light years", "light-year", "light-years", "ly")
_add("length", 1.495978707e11, "au", "astronomical unit", "astronomical units")
_add("mass", 1.0, "kg", "kilogram", "kilograms", "kilo", "kilos")
_add("mass", 0.001, "g", "gram", "grams", "gramme", "grammes")
_add("mass", 1e-6, "mg", "milligram", "milligrams")
_add("mass", 1000.0, "t", "tonne", "tonnes", "metric ton", "metric tons")
_add("mass", 0.45359237, "lb", "lbs", "pound", "pounds")
_add("mass", 0.028349523125, "oz", "ounce", "ounces")
_add("mass", 6.35029318, "st", "stone", "stones")
_add("mass", 907.18474, "short ton", "short tons", "us ton", "us tons")
_add("volume", 1.0, "l", "liter", "liters", "litre", "litres")
_add("volume", 0.001, "ml", "milliliter", "milliliters", "millilitre", "millilitres")
_add("volume", 0.01, "cl", "centiliter", "centiliters", "centilitre", "centilitres")
_add("volume", 0.1, "dl", "deciliter", "deciliters", "decilitre", "decilitres")
_add("volume", 1000.0, "cubic meter", "cubic meters", "cubic metre", "cubic metres", "m3", "m³")
_add("volume", 3.785411784, "gallon", "gallons", "gal", "us gallon", "us gallons")
_add("volume", 4.54609, "imperial gallon", "imperial gallons", "uk gallon", "uk gallons")
_add("volume", 0.946352946, "quart", "quarts", "qt")
_add("volume", 0.473176473, "pint", "pints", "pt", "us pint", "us pints")
_add("volume", 0.56826125, "imperial pint", "imperial pints", "uk pint", "uk pints")
_add("volume", 0.2365882365, "cup", "cups")
_add("volume", 0.0295735295625, "fl oz", "fluid ounce", "fluid ounces")
_add("volume", 0.01478676478125, "tablespoon", "tablespoons", "tbsp")
_add("volume", 0.00492892159375, "teaspoon", "teaspoons", "tsp")
_add("area", 1.0, "square meter", "square meters", "square metre", "square metres", "m2", "m²", "sqm")
_add("area", 1e6, "square kilometer", "square kilometers", "square kilometre", "square kilometres", "km2", "km²")
_add("area", 1e4, "hectare", "hectares", "ha")
_add("area", 4046.8564224, "acre", "acres")
_add("area", 0.09290304, "square foot", "square feet", "sq ft", "ft2", "ft²")
_add("area", 2589988.110336, "square mile", "square miles", "sq mi", "mi2", "mi²")
_add("speed", 1.0, "m/s", "meters per second", "metres per second", "meter per second", "metre per second")
_add("speed", 1000 / 3600, "km/h", "kph", "kmh", "kilometers per hour", "kilometres per hour",
     "kilometer per hour", "kilometre per hour")
_add("speed", 1609.344 / 3600, "mph", "miles per hour", "mile per hour")
_add("speed", 1852 / 3600, "knot", "knots", "kn")
_add("time", 1.0, "s", "sec", "secs", "second", "seconds")
_add("time", 60.0, "min", "mins", "minute", "minutes")
_add("time", 3600.0, "h", "hr", "hrs", "hour", "hours")
_add("time", 86400.0, "day", "days")
_add("time", 604800.0, "week", "weeks")
_add("time", 31557600.0, "year", "years")
_add("time", 0.001, "ms", "millisecond", "milliseconds")
_add("data", 1.0, "byte", "bytes", "b")
_add("data", 1e3, "kb", "kilobyte", "kilobytes")
_add("data", 1e6, "mb", "megabyte", "megabytes")
_add("data", 1e9, "gb", "gigabyte", "gigabytes")
_add("data", 1e12, "tb", "terabyte", "terabytes")
_add("data", 1024.0, "kib", "kibibyte", "kibibytes")
_add("data", 1024.0 ** 2, "mib", "mebibyte", "mebibytes")
_add("data", 1024.0 ** 3, "gib", "gibibyte", "gibibytes")
_add("data", 0.125, "bit", "bits")
_TEMPS = {"c": "C", "°c": "C", "celsius": "C", "degrees celsius": "C", "degree celsius": "C", "centigrade": "C",
          "f": "F", "°f": "F", "fahrenheit": "F", "degrees fahrenheit": "F", "degree fahrenheit": "F",
          "k": "K", "kelvin": "K", "kelvins": "K", "degrees c": "C", "degrees f": "F", "degrees": "C"}
_TEMP_NAME = {"C": "°C", "F": "°F", "K": "K"}

_UNIT_ALT = "|".join(sorted((re.escape(u) for u in list(_UNITS) + list(_TEMPS)), key=len, reverse=True))
_NUM = r"(-?\d+(?:[.,]\d+)*(?:\.\d+)?|a|an|one|two|three|four|five|six|seven|eight|nine|ten|a hundred|a thousand)"
_CONVERT = [
    re.compile(rf"^(?:(?:can you |could you |please )*(?:convert|change|turn|what(?:'s| is)|whats|how much is|"
               rf"how many|how far is|how long is|how heavy is|how big is))?\s*{_NUM}\s*({_UNIT_ALT})\s+"
               rf"(?:in|to|into|as|in terms of|equals how many|is how many|=)\s+(?:a |an )?({_UNIT_ALT})$", re.I),
    re.compile(rf"^how many\s+({_UNIT_ALT})\s+(?:are |is )?(?:there )?(?:in|per)\s+{_NUM}\s*({_UNIT_ALT})$", re.I),
    re.compile(rf"^how many\s+({_UNIT_ALT})\s+(?:are |is )?(?:there )?(?:in|per)\s+(?:a|an|one)\s+({_UNIT_ALT})$",
               re.I),
]


def _num(s: str) -> float:
    s = s.lower().strip()
    if s in ("a", "an", "one"):
        return 1.0
    w = words_to_number(s)
    if w is not None:
        return float(w)
    if re.fullmatch(r"-?\d{1,3}(,\d{3})+(\.\d+)?", s):
        s = s.replace(",", "")
    elif "," in s and "." not in s:
        s = s.replace(",", ".")          # 2,5 km (decimal comma)
    return float(s)


def _unit_label(u: str, value: float) -> str:
    u = u.lower()
    if u in _TEMPS:
        return _TEMP_NAME[_TEMPS[u]]
    return u


def convert(message: str) -> ToolResult | None:
    s = message.strip().rstrip("?.!").strip()
    s = re.sub(r"\s+", " ", s)
    for i, rx in enumerate(_CONVERT):
        m = rx.match(s)
        if not m:
            continue
        if i == 0:
            val, a, b = _num(m.group(1)), m.group(2), m.group(3)
        elif i == 1:
            b, val, a = m.group(1), _num(m.group(2)), m.group(3)
        else:
            b, a, val = m.group(1), m.group(2), 1.0
        return _convert(val, a, b)
    return None


def _convert(val: float, a_shown: str, b_shown: str) -> ToolResult | None:
    a, b = a_shown.lower(), b_shown.lower()
    if a in _TEMPS and b in _TEMPS and (a not in _UNITS or b not in _UNITS or a in ("c", "f", "k")):
        ta, tb = _TEMPS[a], _TEMPS[b]
        kelvin = {"C": val + 273.15, "F": (val - 32) * 5 / 9 + 273.15, "K": val}[ta]
        out = {"C": kelvin - 273.15, "F": (kelvin - 273.15) * 9 / 5 + 32, "K": kelvin}[tb]
        out = round(out, 2)
        return ToolResult("units", f"{fmt_number(val)} {_TEMP_NAME[ta]} = {fmt_number(out)} {_TEMP_NAME[tb]}",
                          fmt_number(out))
    if a not in _UNITS or b not in _UNITS:
        return None
    da, fa = _UNITS[a]
    db, fb = _UNITS[b]
    if da != db:
        return ToolResult("units", f"I can't convert {a} into {b} — one is a {da}, the other a {db}.")
    out = val * fa / fb
    digits = 6 if abs(out) < 1 else 4
    out_r = float(f"{out:.{digits}g}") if out != 0 else 0.0
    return ToolResult("units", f"{fmt_number(val)} {a_shown} = {fmt_number(out_r)} {b_shown}", fmt_number(out_r))


# ---------------------------------------------------------------------------
# dates and times
# ---------------------------------------------------------------------------

_MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                       "september", "october", "november", "december"], 1)}
_MONTHS.update({k[:3]: v for k, v in list(_MONTHS.items())})
_MONTHS["sept"] = 9
_HOLIDAYS = {"christmas": (12, 25), "christmas eve": (12, 24), "new year": (1, 1), "new year's day": (1, 1),
             "new years": (1, 1), "new year's eve": (12, 31), "new years eve": (12, 31), "halloween": (10, 31),
             "valentine's day": (2, 14), "valentines day": (2, 14), "valentine's": (2, 14),
             "independence day": (7, 4), "st patrick's day": (3, 17), "saint patrick's day": (3, 17)}
_WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _fmt_date(d: dt.date) -> str:
    return f"{_WEEKDAYS[d.weekday()]}, {d.day} {d.strftime('%B')} {d.year}"


def _parse_date(text: str, today: dt.date) -> dt.date | None:
    t = text.lower().strip().strip("?.! ").replace(",", "")
    t = re.sub(r"^(?:the |on )", "", t)
    if t in ("today", "now"):
        return today
    if t == "tomorrow":
        return today + dt.timedelta(days=1)
    if t == "yesterday":
        return today - dt.timedelta(days=1)
    if t in ("the day after tomorrow",):
        return today + dt.timedelta(days=2)
    hol = t.replace("the ", "")
    if hol in _HOLIDAYS:
        mo, da = _HOLIDAYS[hol]
        d = dt.date(today.year, mo, da)
        return d if d >= today else dt.date(today.year + 1, mo, da)
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", t)
    if m:
        y, mo, da = map(int, m.groups())
    else:
        m = re.fullmatch(r"(\d{1,2})(?:st|nd|rd|th)?(?: of)? ([a-z]+)(?: (\d{4}))?", t)
        m2 = re.fullmatch(r"([a-z]+) (\d{1,2})(?:st|nd|rd|th)?(?: (\d{4}))?", t)
        m3 = re.fullmatch(r"(\d{1,2})[./](\d{1,2})[./](\d{4})", t)
        if m and m.group(2) in _MONTHS:
            da, mo, y = int(m.group(1)), _MONTHS[m.group(2)], int(m.group(3)) if m.group(3) else None
        elif m2 and m2.group(1) in _MONTHS:
            mo, da, y = _MONTHS[m2.group(1)], int(m2.group(2)), int(m2.group(3)) if m2.group(3) else None
        elif m3:
            da, mo, y = int(m3.group(1)), int(m3.group(2)), int(m3.group(3))   # European day.month.year
        else:
            return None
        if y is None:
            try:
                d = dt.date(today.year, mo, da)
            except ValueError:
                return None
            return d if d >= today else dt.date(today.year + 1, mo, da)
    try:
        return dt.date(y, mo, da)
    except ValueError:
        return None


_TIME_Q = re.compile(r"^(?:(?:do you know |can you tell me |tell me )?(?:what(?:'s| is)|whats) the time(?: now| right now)?|"
                     r"what time is it(?: now| right now)?|(?:do you know |can you tell me )?what time it is|"
                     r"current time|time please|the time)$", re.I)
_DATE_Q = re.compile(r"^(?:(?:can you tell me |tell me |do you know )?(?:what(?:'s| is)|whats) (?:the |today's |todays )?"
                     r"(?:date|day)(?: today| it is| is it)?(?: today)?|what date is it(?: today)?|what day is (?:it|today)(?: today)?|"
                     r"which day is (?:it|today)|what(?:'s| is) today|today's date|todays date|what date is today|"
                     r"(?:do you know |can you tell me )?what day it is(?: today)?|date please|the date)$", re.I)
_YEAR_Q = re.compile(r"^(?:what|which) year is (?:it|this)(?: now)?$|^what(?:'s| is) the (?:current )?year$", re.I)
_MONTH_Q = re.compile(r"^(?:what|which) month is (?:it|this)(?: now)?$", re.I)
_WEEKDAY_OF = re.compile(r"^(?:what|which) (?:day(?: of the week)?|weekday) (?:is|was|will be|falls on|is it on|was it on) "
                         r"(?P<d>.+?)(?: on)?$", re.I)
_DAYS_UNTIL = re.compile(r"^how (?:many|much) (?:days|weeks)(?: are)? (?:(?:are )?(?:left |there )?(?:until|till|til|before|to)) "
                         r"(?P<d>.+)$|^how long (?:until|till|before|to) (?P<d2>.+)$", re.I)
_DAYS_SINCE = re.compile(r"^how many days (?:have passed |has it been |since|ago was) ?(?:since )?(?P<d>.+)$", re.I)
_DAYS_BETWEEN = re.compile(r"^how many days (?:are there )?between (?P<a>.+?) and (?P<b>.+)$", re.I)


def date_answer(message: str, now: dt.datetime | None = None) -> ToolResult | None:
    now = now or dt.datetime.now()
    today = now.date()
    s = re.sub(r"\s+", " ", message.strip().rstrip("?.!").strip())
    if _TIME_Q.match(s):
        return ToolResult("date", f"It's {now.strftime('%H:%M')} (on this computer's clock).", now.strftime("%H:%M"))
    if _DATE_Q.match(s):
        return ToolResult("date", f"Today is {_fmt_date(today)}.", today.isoformat())
    tm = re.fullmatch(r"(?:and )?(?:what(?:'s| is)|whats) (?:the )?(?:date|day) (?:is it )?(?P<w>tomorrow|yesterday|the day after tomorrow)|"
                      r"(?:and )?what (?:day|date) (?:is|was|will be) (?:it )?(?P<w2>tomorrow|yesterday|the day after tomorrow)|"
                      r"(?:and )?what (?:was|is|will be) the (?:date|day) (?P<w4>tomorrow|yesterday|the day after tomorrow)|"
                      r"(?:and )?(?:what(?:'s| is)|whats|which day is) (?P<w5>the day after tomorrow)|"
                      r"(?:and )?(?P<w3>tomorrow|yesterday)\??", s, re.I)
    if tm:                                     # "what day is it tomorrow?"
        w = (tm.group("w") or tm.group("w2") or tm.group("w3") or tm.group("w4") or tm.group("w5")).lower()
        shift = {"tomorrow": 1, "yesterday": -1, "the day after tomorrow": 2}[w]
        day = today + dt.timedelta(days=shift)
        verb = "was" if shift < 0 else "is"
        return ToolResult("date", f"{w[:1].upper() + w[1:]} {verb} {_fmt_date(day)}.", day.isoformat())
    if _YEAR_Q.match(s):
        return ToolResult("date", f"It's {today.year}.", str(today.year))
    if _MONTH_Q.match(s):
        return ToolResult("date", f"It's {today.strftime('%B')}.", today.strftime("%B"))
    m = _WEEKDAY_OF.match(s)
    if m:
        d = _parse_date(m.group("d"), today)
        if d:
            verb = "is" if d >= today else "was"
            return ToolResult("date", f"{d.day} {d.strftime('%B')} {d.year} {verb} a {_WEEKDAYS[d.weekday()]}.",
                              _WEEKDAYS[d.weekday()])
    m = _DAYS_BETWEEN.match(s)
    if m:
        a, b = _parse_date(m.group("a"), today), _parse_date(m.group("b"), today)
        if a and b:
            n = abs((b - a).days)
            return ToolResult("date", f"There are {n:,} days between {_fmt_date(a)} and {_fmt_date(b)}.", str(n))
    m = _DAYS_UNTIL.match(s)
    if m:
        target = m.group("d") or m.group("d2")
        d = _parse_date(target, today)
        if d:
            n = (d - today).days
            if n == 0:
                return ToolResult("date", "That's today!", "0")
            if n < 0:
                return ToolResult("date", f"That was {-n:,} days ago ({_fmt_date(d)}).", str(n))
            w = n / 7
            weeks = (f" — exactly {round(w)} weeks" if n % 7 == 0 else f" — about {w:.1f} weeks".replace(".0 weeks", " weeks")) \
                if n >= 14 else ""
            return ToolResult("date", f"{n:,} day{'s' if n != 1 else ''} until {_fmt_date(d)}{weeks}.", str(n))
    m = _DAYS_SINCE.match(s)
    if m:
        d = _parse_date(m.group("d"), today)
        if d and d <= today:
            n = (today - d).days
            return ToolResult("date", f"{n:,} days have passed since {_fmt_date(d)}.", str(n))
    return None


# ---------------------------------------------------------------------------
# small exact tools: number facts, currencies (honestly), phrases, synonyms
# ---------------------------------------------------------------------------

_NUMQ = re.compile(r"^(?:is|are)\s+(?P<n>-?\d{1,12})\s+(?:a\s+|an\s+)?(?P<what>prime(?: number)?|even(?: number)?|"
                   r"odd(?: number)?|perfect square|square number)\s*\??$|"
                   r"^(?:is|does)\s+(?P<a>\d{1,12})\s+(?:divisible by|divide by)\s+(?P<b>\d{1,9})\s*\??$|"
                   r"^(?:what(?:'s| is)\s+)?(?:the\s+)?factorial of (?P<f>\d{1,3})\s*\??$|^(?P<f2>\d{1,3})\s*!\s*\??$", re.I)


def _is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    r = int(math.isqrt(n))
    return all(n % k for k in range(3, r + 1, 2))


def number_fact(message: str) -> ToolResult | None:
    """"is 17 a prime number?", "is 10 divisible by 3?", "factorial of 5" — computed, never looked up."""
    m = _NUMQ.match(message.strip().rstrip(".!"))
    if not m:
        return None
    if m.group("n"):
        n, what = int(m.group("n")), m.group("what").lower()
        if what.startswith("prime"):
            if _is_prime(n):
                return ToolResult("calc", f"Yes — {n} is a prime number.", "yes")
            if n < 2:
                return ToolResult("calc", f"No — {n} is not a prime number (primes start at 2).", "no")
            d = next(k for k in range(2, int(math.isqrt(n)) + 1) if n % k == 0)
            return ToolResult("calc", f"No — {n} is not prime: it's {d} × {n // d}.", "no")
        if what.startswith("even"):
            return ToolResult("calc", f"{'Yes' if n % 2 == 0 else 'No'} — {n} is {'even' if n % 2 == 0 else 'odd'}.",
                              "yes" if n % 2 == 0 else "no")
        if what.startswith("odd"):
            return ToolResult("calc", f"{'Yes' if n % 2 else 'No'} — {n} is {'odd' if n % 2 else 'even'}.",
                              "yes" if n % 2 else "no")
        r = math.isqrt(abs(n))
        ok = n >= 0 and r * r == n
        return ToolResult("calc", f"Yes — {n} = {r} × {r}." if ok else f"No — {n} is not a perfect square.",
                          "yes" if ok else "no")
    if m.group("a"):
        a, b = int(m.group("a")), int(m.group("b"))
        if b == 0:
            return ToolResult("calc", "Nothing is divisible by 0 — dividing by zero isn't defined.", "no")
        if a % b == 0:
            return ToolResult("calc", f"Yes — {a} ÷ {b} = {a // b}.", "yes")
        return ToolResult("calc", f"No — {a} ÷ {b} = {a // b} remainder {a % b}.", "no")
    f = int(m.group("f") or m.group("f2"))
    if f > 170:
        return ToolResult("calc", f"{f}! is far too large to write out — it has more than 300 digits.", None)
    return ToolResult("calc", f"{f}! = {fmt_number(math.factorial(f))}.", str(math.factorial(f)))


_MONEY = re.compile(r"^(?:what(?:'s| is)\s+|how much is\s+|convert\s+)?\d[\d.,]*\s*(?:€|\$|£|¥)?\s*"
                    r"(?:euros?|eur|dollars?|usd|pounds?|gbp|yen|jpy|francs?|chf|yuan|rupees?|pesos?|bitcoins?|btc)\s+"
                    r"(?:in|to|into)\s+(?:euros?|eur|dollars?|usd|pounds?|gbp|yen|jpy|francs?|chf|yuan|rupees?|pesos?)\s*\??$|"
                    r"^(?:what(?:'s| is) the )?exchange rate\b", re.I)


def money(message: str) -> ToolResult | None:
    """Currency conversions need today's rates — said honestly instead of a guess."""
    if not _MONEY.match(message.strip()):
        return None
    return ToolResult("money", "I can't convert currencies reliably — exchange rates change every day, and I work "
                               "offline without live data. A bank or currency app will have today's rate.", None)


_PHRASES = {
    "hello": {"spanish": "hola", "french": "bonjour", "german": "hallo", "italian": "ciao", "portuguese": "olá"},
    "hi": {"spanish": "hola", "french": "salut", "german": "hallo", "italian": "ciao", "portuguese": "oi"},
    "goodbye": {"spanish": "adiós", "french": "au revoir", "german": "auf Wiedersehen", "italian": "arrivederci",
                "portuguese": "adeus"},
    "bye": {"spanish": "adiós", "french": "salut", "german": "tschüss", "italian": "ciao", "portuguese": "tchau"},
    "thank you": {"spanish": "gracias", "french": "merci", "german": "danke", "italian": "grazie",
                  "portuguese": "obrigado / obrigada"},
    "thanks": {"spanish": "gracias", "french": "merci", "german": "danke", "italian": "grazie",
               "portuguese": "obrigado / obrigada"},
    "please": {"spanish": "por favor", "french": "s'il vous plaît", "german": "bitte", "italian": "per favore",
               "portuguese": "por favor"},
    "yes": {"spanish": "sí", "french": "oui", "german": "ja", "italian": "sì", "portuguese": "sim"},
    "no": {"spanish": "no", "french": "non", "german": "nein", "italian": "no", "portuguese": "não"},
    "good morning": {"spanish": "buenos días", "french": "bonjour", "german": "guten Morgen", "italian": "buongiorno",
                     "portuguese": "bom dia"},
    "good night": {"spanish": "buenas noches", "french": "bonne nuit", "german": "gute Nacht", "italian": "buona notte",
                   "portuguese": "boa noite"},
    "how are you": {"spanish": "¿cómo estás?", "french": "comment ça va ?", "german": "wie geht's?",
                    "italian": "come stai?", "portuguese": "como vai?"},
    "i love you": {"spanish": "te quiero", "french": "je t'aime", "german": "ich liebe dich", "italian": "ti amo",
                   "portuguese": "eu te amo"},
    "sorry": {"spanish": "lo siento", "french": "désolé", "german": "Entschuldigung", "italian": "scusa",
              "portuguese": "desculpa"},
    "excuse me": {"spanish": "disculpe", "french": "excusez-moi", "german": "Entschuldigung", "italian": "mi scusi",
                  "portuguese": "com licença"},
    "cheers": {"spanish": "¡salud!", "french": "santé !", "german": "prost!", "italian": "salute!",
               "portuguese": "saúde!"},
    "welcome": {"spanish": "bienvenido", "french": "bienvenue", "german": "willkommen", "italian": "benvenuto",
                "portuguese": "bem-vindo"},
    "my name is": {"spanish": "me llamo", "french": "je m'appelle", "german": "ich heiße", "italian": "mi chiamo",
                   "portuguese": "meu nome é"},
}
_LANGS = {"spanish": "Spanish", "french": "French", "german": "German", "italian": "Italian", "portuguese": "Portuguese"}
_TRANSLATE = re.compile(r"^(?:how do (?:you|i) say|translate|what(?:'s| is))\s+[\"“']?(?P<p>[a-z' ]{1,30}?)[\"”']?\s+"
                        r"(?:in|to|into)\s+(?P<l>[a-z]+)\s*\??$", re.I)


def translate(message: str) -> ToolResult | None:
    """"How do you say thank you in French?" from a small phrase list; anything else honestly."""
    m = _TRANSLATE.match(message.strip().rstrip(".!"))
    if not m:
        return None
    phrase, lang = m.group("p").strip().lower(), m.group("l").lower()
    if lang not in _LANGS and lang not in ("english", "chinese", "japanese", "russian", "arabic", "dutch", "turkish",
                                            "polish", "korean", "hindi", "swedish", "greek"):
        return None
    hit = _PHRASES.get(phrase, {}).get(lang)
    if hit:
        return ToolResult("translate", f"In {_LANGS[lang]}, “{phrase}” is “{hit}”.", hit)
    return ToolResult("translate", f"I only know a few everyday phrases in other languages — “{phrase}” in "
                                   f"{lang.capitalize()} isn't among them, sorry. A dictionary app will know.", None)


_SYNONYMS = {
    "happy": ["glad", "cheerful", "joyful", "content", "delighted"], "sad": ["unhappy", "down", "gloomy", "miserable"],
    "big": ["large", "huge", "enormous", "vast"], "small": ["little", "tiny", "compact", "minor"],
    "good": ["great", "fine", "excellent", "decent"], "bad": ["poor", "awful", "terrible", "unpleasant"],
    "fast": ["quick", "rapid", "speedy", "swift"], "slow": ["unhurried", "sluggish", "leisurely"],
    "smart": ["clever", "intelligent", "bright", "sharp"], "beautiful": ["lovely", "gorgeous", "pretty", "stunning"],
    "important": ["significant", "essential", "key", "crucial"], "angry": ["annoyed", "furious", "irritated", "mad"],
    "tired": ["exhausted", "weary", "worn out", "sleepy"], "funny": ["amusing", "hilarious", "witty", "comical"],
    "easy": ["simple", "straightforward", "effortless"], "hard": ["difficult", "tough", "challenging"],
    "interesting": ["fascinating", "intriguing", "engaging"], "boring": ["dull", "tedious", "monotonous"],
    "scared": ["afraid", "frightened", "fearful"], "old": ["aged", "elderly", "ancient", "vintage"],
    "new": ["fresh", "recent", "modern", "novel"], "rich": ["wealthy", "affluent", "well-off"],
    "help": ["assist", "support", "aid"], "say": ["state", "mention", "tell", "remark"],
    "use": ["employ", "utilise", "apply"], "show": ["display", "reveal", "demonstrate"],
    "start": ["begin", "launch", "kick off"], "end": ["finish", "conclude", "close"],
    "nice": ["pleasant", "kind", "lovely", "agreeable"], "great": ["excellent", "superb", "fantastic", "terrific"],
    "love": ["adore", "cherish", "be fond of"], "hate": ["detest", "loathe", "dislike"],
    "think": ["believe", "consider", "reckon"], "very": ["extremely", "really", "highly"],
    "strong": ["powerful", "sturdy", "robust"], "weak": ["frail", "feeble", "fragile"],
    "quiet": ["silent", "calm", "peaceful"], "loud": ["noisy", "booming", "deafening"],
    "cold": ["chilly", "freezing", "icy"], "hot": ["warm", "boiling", "scorching"],
    "sure": ["certain", "confident", "positive"], "problem": ["issue", "difficulty", "trouble"],
}
_SYN_Q = re.compile(r"^(?:what(?:'s| is| are)\s+)?(?:an?\s+|some\s+|another\s+)?(?:synonyms?|other words?|another word)\s+"
                    r"(?:for|of)\s+[\"“']?(?P<w>[a-z-]+)[\"”']?\s*\??$|^(?:give me|tell me)\s+(?:a\s+)?synonyms?\s+for\s+"
                    r"(?P<w2>[a-z-]+)\s*\??$", re.I)


def synonyms(message: str) -> ToolResult | None:
    m = _SYN_Q.match(message.strip().rstrip(".!"))
    if not m:
        return None
    w = (m.group("w") or m.group("w2")).lower()
    syn = _SYNONYMS.get(w)
    if syn:
        return ToolResult("words", f"Some other words for “{w}”: {', '.join(syn[:-1])} and {syn[-1]}.", syn[0])
    return ToolResult("words", f"I don't have synonyms for “{w}” in my word list, sorry — a thesaurus will help.", None)


def tool_answer(message: str, now: dt.datetime | None = None) -> ToolResult | None:
    """The first tool that recognises the message (dates, units, number facts, money, words, then arithmetic)."""
    return (date_answer(message, now) or convert(message) or number_fact(message) or money(message)
            or translate(message) or synonyms(message) or calculate(message))
