"""Render a portable comparison report from verified research in JSON."""

import argparse
import json
import re
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from html import escape
from pathlib import Path
from string import Template
from urllib.parse import urlsplit

IDENTIFIER = re.compile(r"[a-z][a-z0-9-]*\Z")
TENTH = Decimal("0.1")
DIGITS = "零一二三四五六七八九"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def chinese_number(number, leading=True):
    if number < 10:
        return DIGITS[number]
    for divisor, unit in ((10_000, "万"), (1000, "千"), (100, "百"), (10, "十")):
        if number >= divisor:
            quotient, remainder = divmod(number, divisor)
            prefix = "" if leading and number < 20 else chinese_number(quotient)
            if not remainder:
                return prefix + unit
            zero = "零" if remainder < divisor // 10 else ""
            return prefix + unit + zero + chinese_number(remainder, leading=False)


def item_text(item, key):
    value = item.get(key)
    require(isinstance(value, str) and value.strip(), f"{key} must be non-empty text")
    return value.strip()


def object_rows(data, key, minimum=0):
    rows = data.get(key)
    require(isinstance(rows, list) and len(rows) >= minimum, f"{key} needs at least {minimum} entries")
    require(all(isinstance(row, dict) for row in rows), f"{key} entries must be objects")
    return rows


def identifiers(values, allowed, field):
    require(
        isinstance(values, list) and all(isinstance(value, str) and value in allowed for value in values),
        f"{field} must list known IDs",
    )
    return list(dict.fromkeys(values))


def index_by_id(rows, field):
    indexed = {}
    for row in rows:
        key = item_text(row, "id")
        require(IDENTIFIER.fullmatch(key), f"Invalid {field} ID: {key}")
        require(key not in indexed, f"Duplicate {field} ID: {key}")
        indexed[key] = row
    return indexed


def normalize_score(value, label):
    if value is None:
        return None
    require(type(value) in (int, Decimal), f"{label} must be a number or null")
    value = Decimal(value)
    require(value.is_finite() and 0 <= value <= 100, f"{label} must be in 0–100")
    return (value if value else Decimal(0)).quantize(TENTH, rounding=ROUND_HALF_UP)


def load_report(path):
    data = json.loads(path.read_text(encoding="utf-8-sig"), parse_float=Decimal)
    require(isinstance(data, dict), "Report JSON must be an object")
    report_date = item_text(data, "as_of")
    require(re.fullmatch(r"\d{4}-\d{2}-\d{2}", report_date), "as_of must use YYYY-MM-DD")
    date.fromisoformat(report_date)

    source_index = index_by_id(object_rows(data, "sources", 1), "source")
    for source in source_index.values():
        url = item_text(source, "url")
        parsed = urlsplit(url)
        require(
            parsed.scheme in ("https", "http") and parsed.hostname and not parsed.username
            and not parsed.password and not re.search(r"\s", url),
            f"Source {source['id']} needs an HTTP(S) URL without credentials",
        )
        item_text(source, "title")

    dimensions = index_by_id(object_rows(data, "dimensions", 1), "dimension")
    models = object_rows(data, "models", 2)
    for model in models:
        label = item_text(model, "name")
        scores = model.get("scores")
        citations = model.get("score_sources")
        require(isinstance(scores, dict) and scores.keys() == dimensions.keys(),
                f"Model {label} scores must match every dimension ID")
        require(isinstance(citations, dict) and citations.keys() == dimensions.keys(),
                f"Model {label} score_sources must match every dimension ID")
        model["provisional"] = identifiers(model.get("provisional", []), dimensions, f"{label}.provisional")
        for key in dimensions:
            scores[key] = normalize_score(scores[key], f"{label}.{key}")
            citations[key] = identifiers(citations[key], source_index, f"{label}.{key}.score_sources")
            if scores[key] is not None:
                require(citations[key], f"{label}.{key} needs a score source")
            else:
                require(key not in model["provisional"], f"{label}.{key} is missing, so cannot be provisional")
        model["total"] = sum(scores.values()) if all(value is not None for value in scores.values()) else None

    for section in ("dimensions", "models", "scenarios", "costs", "evidence"):
        for row in object_rows(data, section):
            row["sources"] = identifiers(row.get("sources"), source_index, f"{section}.sources")
    methodology = data.get("methodology")
    require(isinstance(methodology, list) and methodology
            and all(isinstance(value, str) and value.strip() for value in methodology),
            "methodology needs at least one text paragraph")
    return data, dimensions, models, source_index


def paragraphs(content):
    return "\n".join(f"<p>{escape(line.strip())}</p>" for line in content.splitlines() if line.strip())


def source_link(source):
    url = escape(source["url"], quote=True)
    title = escape(source["title"])
    return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{title}</a>'


def source_links(ids, sources):
    if not ids:
        return ""
    return '<p class="refs">' + " · ".join(source_link(sources[key]) for key in ids) + "</p>"


def table(headers, rows, style, label):
    heading = "".join(f'<th scope="col">{escape(header)}</th>' for header in headers)
    return (
        f'<div class="tablebox" tabindex="0" role="region" aria-label="{escape(label)}">'
        f'<table class="{style}"><thead><tr>{heading}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>'
    )


def text_row(heading, *cells):
    columns = "".join(f"<td>{cell}</td>" for cell in cells)
    return f'<tr><th scope="row">{escape(heading)}</th>{columns}</tr>'


def ranks(values):
    positions = {}
    applicable = sorted((value for value in values if value is not None), reverse=True)
    for index, value in enumerate(applicable, start=1):
        positions.setdefault(value, index)
    return positions


def descending(value):
    return value is None, -value if value is not None else Decimal(0)


def render_matrix(dimensions, models):
    column_ranks = {key: ranks(model["scores"][key] for model in models) for key in dimensions}
    total_ranks = ranks(model["total"] for model in models)
    headers = ["总榜名次与型号", *(item["name"] for item in dimensions.values()), f"总分 / {100 * len(dimensions)}"]
    rows = []
    for model in sorted(models, key=lambda model: descending(model["total"])):
        cells = []
        for key, positions in column_ranks.items():
            value = model["scores"][key]
            if value is None:
                cells.append('<td class="score" aria-label="缺测">—</td>')
                continue
            position = positions[value]
            mark = '<sup aria-label="暂定">†</sup>' if key in model["provisional"] else ""
            style = "score best" if position == 1 else "score"
            cells.append(f'<td class="{style}"><span>{value:.1f}</span>'
                         f'<small>（第{chinese_number(position)}）{mark}</small></td>')
        total = model["total"]
        formatted_total = "—" if total is None else f"{total:.1f}"
        position = "—" if total is None else total_ranks[total]
        name = escape(item_text(model, "name"))
        vendor = escape(item_text(model, "vendor"))
        rows.append(f'<tr><th scope="row"><span class="place">{position}</span>'
                    f'<span>{name}<small>{vendor}</small></span></th>'
                    f'{"".join(cells)}<td class="total score">{formatted_total}</td></tr>')
    return table(headers, rows, "matrix", "能力总榜，可横向滚动")


def render_ranking(dimensions, models, sources):
    rows = []
    for key, dimension in dimensions.items():
        groups = {}
        for model in sorted(models, key=lambda model: descending(model["scores"][key])):
            mark = "†" if key in model["provisional"] else ""
            groups.setdefault(model["scores"][key], []).append(escape(item_text(model, "name")) + mark)
        missing = groups.pop(None, [])
        ordered = " › ".join(" ≈ ".join(group) for group in groups.values())
        parts = [f'<div class="order">{ordered}</div>'] if ordered else []
        if missing:
            parts.append(f'<p class="notes">缺测 {"、".join(missing)}</p>')
        parts.extend((paragraphs(item_text(dimension, "finding")), source_links(dimension["sources"], sources)))
        rows.append(text_row(item_text(dimension, "name"), "".join(parts)))
    return table(["维度", "顺序与主要取舍"], rows, "ranks", "各维度排行")


def render_score_details(dimensions, models, sources):
    items = []
    for model in sorted(models, key=lambda model: descending(model["total"])):
        citations = []
        for key, ids in model["score_sources"].items():
            if ids:
                links = " · ".join(source_link(sources[source_id]) for source_id in ids)
                citations.append(f'<li>{escape(dimensions[key]["name"])} · {links}</li>')
        note = "".join(citations) or "<li>本报告没有可用的分项来源。</li>"
        items.append(f'<li><strong>{escape(model["name"])}</strong><ul>{note}</ul></li>')
    return '<details class="score-details"><summary>逐项评分来源</summary><ul>' + "".join(items) + "</ul></details>"


def render_choices(items, sources):
    rows = []
    for choice in items:
        first = f'<strong>{escape(item_text(choice, "first"))}</strong>{paragraphs(item_text(choice, "first_reason"))}'
        second = f'<strong>{escape(item_text(choice, "second"))}</strong>{paragraphs(item_text(choice, "second_reason"))}'
        rows.append(text_row(item_text(choice, "name"), first, second + source_links(choice["sources"], sources)))
    if not rows:
        return '<p class="notes">本报告未指定场景。</p>'
    return table(["用途", "首选", "次选"], rows, "scenarios", "场景选型表")


def render_costs(items, sources):
    if not items:
        return '<p class="notes">暂无同口径成本可排行。</p>'
    rows = []
    for item in items:
        label = escape(item_text(item, "model"))
        if "rank" in item:
            label += f'<br><small>{escape(item_text(item, "rank"))}</small>'
        price = escape(item_text(item, "unit_price"))
        cost = escape(item_text(item, "example_cost"))
        rows.append(f'<tr><th scope="row">{label}</th><td>{price}</td>'
                    f'<td class="money">{cost}</td><td>{source_links(item["sources"], sources)}</td></tr>')
    return table(["模型", "输入 / 输出计价", "示例费用", "计费来源"], rows, "prices", "成本排行")


def render(data, dimensions, models, sources):
    stamped = date.fromisoformat(data["as_of"])
    count = len(dimensions)
    model_rows = [
        text_row(item_text(model, "vendor"), escape(item_text(model, "name")),
                 paragraphs(item_text(model, "availability")) + source_links(model["sources"], sources))
        for model in models
    ]
    evidence = [
        f'<article><h3>{escape(item_text(item, "title"))}</h3>'
        f'{paragraphs(item_text(item, "text"))}{source_links(item["sources"], sources)}</article>'
        for item in data["evidence"]
    ]
    source_index = '<ol class="sources-list">' + "".join(
        f'<li>{source_link(source)}</li>' for source in sources.values()
    ) + "</ol>"
    template = Path(__file__).resolve().parents[1] / "assets" / "report.html"
    return Template(template.read_text(encoding="utf-8")).substitute(
        title=escape(item_text(data, "title")),
        date=stamped.isoformat(),
        display_date=f"{stamped.year} 年 {stamped.month} 月 {stamped.day} 日",
        summary=escape(item_text(data, "summary")),
        choices=render_choices(data["scenarios"], sources),
        models=table(["厂商", "主参评型号", "版本与入口"], model_rows, "models", "参评模型"),
        ranking=render_ranking(dimensions, models, sources),
        score_title=f"{chinese_number(count)}维总榜",
        score_intro=f"每项满分 100，{chinese_number(count)}项等权相加，满分 {100 * count}。括号里是该列名次，行按总分降序，缺测总分放在表尾。",
        matrix=render_matrix(dimensions, models),
        methodology="".join(paragraphs(item) for item in data["methodology"]),
        score_details=render_score_details(dimensions, models, sources),
        cost_context=escape(item_text(data, "cost_context")),
        costs=render_costs(data["costs"], sources),
        evidence="".join(evidence),
        sources=source_index,
    )


def main():
    parser = argparse.ArgumentParser(description="Render an evidence-backed model ranking as standalone HTML.")
    parser.add_argument("input", type=Path, help="UTF-8 report JSON")
    parser.add_argument("output", type=Path, help="output .html file")
    args = parser.parse_args()
    try:
        require(args.output.suffix.lower() == ".html", "Output needs a .html extension")
        require(args.input.resolve() != args.output.resolve(), "Choose different input and output paths")
        result = render(*load_report(args.input))
        args.output.write_text(result, encoding="utf-8")
    except (OSError, ValueError) as error:
        parser.exit(1, f"Cannot render report: {error}\n")


if __name__ == "__main__":
    main()
