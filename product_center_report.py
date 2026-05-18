# -*- coding: utf-8 -*-

import html
import os
import platform
import re
import sys
import time
import traceback
import unittest
from datetime import datetime
from io import StringIO
from pathlib import Path
from shared_styles import COLORS


REPORT_DIR = Path(__file__).resolve().parent / "reports"


class TeeStream:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for stream in self.streams:
            stream.write(data)
            if "\n" in data:
                stream.flush()
        return len(data)

    def flush(self):
        for stream in self.streams:
            stream.flush()

    def isatty(self):
        return any(getattr(stream, "isatty", lambda: False)() for stream in self.streams)


class ProductCenterHtmlResult(unittest.TextTestResult):
    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.records = []
        self.started_at = time.time()
        self._start_times = {}
        self._recorded_tests = set()

    def startTest(self, test):
        self._start_times[id(test)] = time.time()
        super().startTest(test)

    def addSuccess(self, test):
        super().addSuccess(test)
        if id(test) not in self._recorded_tests:
            self._add_record("passed", test)

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._add_record("failed", test, err)

    def addError(self, test, err):
        super().addError(test, err)
        self._add_record("error", test, err)

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._add_record("skipped", test, message=reason)

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is None:
            return
        status = "failed" if issubclass(err[0], test.failureException) else "error"
        self._add_record(status, subtest, err, parent=test)

    def _add_record(self, status, test, err=None, message="", parent=None):
        self._recorded_tests.add(id(test))
        started = self._start_times.get(id(parent or test), self.started_at)
        self.records.append(
            {
                "status": status,
                "name": str(test),
                "id": getattr(test, "id", lambda: str(test))(),
                "parent": getattr(parent, "id", lambda: "")() if parent else "",
                "duration": max(0.0, time.time() - started),
                "message": message,
                "traceback": "".join(traceback.format_exception(*err)) if err else "",
            }
        )


class ProductCenterHtmlRunner(unittest.TextTestRunner):
    resultclass = ProductCenterHtmlResult

    def __init__(self, *args, report_dir=REPORT_DIR, **kwargs):
        super().__init__(*args, **kwargs)
        self.report_dir = Path(report_dir)

    def run(self, test):
        stdout_buffer = StringIO()
        stderr_buffer = StringIO()
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        sys.stdout = TeeStream(original_stdout, stdout_buffer)
        sys.stderr = TeeStream(original_stderr, stderr_buffer)
        try:
            result = super().run(test)
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr

        report_path = write_html_report(
            result,
            stdout_text=stdout_buffer.getvalue(),
            stderr_text=stderr_buffer.getvalue(),
            report_dir=self.report_dir,
        )
        self.stream.writeln(f"\n可视化测试报告：{report_path}")
        return result


def write_html_report(result, stdout_text="", stderr_text="", report_dir=REPORT_DIR):
    report_dir = Path(report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    device_suffix = report_device_suffix()
    report_path = report_dir / f"product_center_report_{timestamp}{device_suffix}.html"
    html_text = build_html_report(result, stdout_text, stderr_text)
    report_path.write_text(html_text, encoding="utf-8")
    latest_path = report_dir / "latest_product_center_report.html"
    latest_path.write_text(html_text, encoding="utf-8")
    return report_path


def report_device_suffix():
    device = os.getenv("DEVICE_UDID") or os.getenv("DEVICE_NAME") or ""
    device = re.sub(r"[^0-9A-Za-z._-]+", "_", device.strip())
    return f"_{device}" if device else ""


def build_html_report(result, stdout_text, stderr_text):
    records = getattr(result, "records", [])
    if records:
        total = len(records)
        failures = sum(1 for record in records if record["status"] == "failed")
        errors = sum(1 for record in records if record["status"] == "error")
        skipped = sum(1 for record in records if record["status"] == "skipped")
        passed = sum(1 for record in records if record["status"] == "passed")
    else:
        total = result.testsRun
        failures = len(result.failures)
        errors = len(result.errors)
        skipped = len(result.skipped)
        passed = max(0, total - failures - errors - skipped)
    duration = max(0.0, time.time() - getattr(result, "started_at", time.time()))
    status = "PASSED" if result.wasSuccessful() else "FAILED"

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>产品中心自动化测试报告</title>
  <style>
    :root {{
      --bg: #f6f7fb;
      --panel: #ffffff;
      --text: #1f2937;
      --muted: #64748b;
      --line: #e5e7eb;
      --pass: {COLORS['status']['pass']};
      --fail: {COLORS['status']['fail']};
      --skip: {COLORS['status']['skip']};
      --error: {COLORS['status']['error']};
      --blue: {COLORS['semantic']['blue']};
      --bg-lighter: #f8fafc;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Segoe UI, Microsoft YaHei, Arial, sans-serif; background: var(--bg); color: var(--text); }}
    header {{ padding: 28px 32px 20px; background: #101827; color: white; }}
    h1 {{ margin: 0 0 8px; font-size: 28px; font-weight: 700; }}
    .meta {{ color: #cbd5e1; font-size: 14px; }}
    main {{ padding: 24px 32px 40px; }}
    .summary {{ display: grid; grid-template-columns: repeat(6, minmax(120px, 1fr)); gap: 12px; margin-bottom: 22px; }}
    .metric {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 16px; }}
    .metric strong {{ display: block; font-size: 26px; line-height: 1; margin-bottom: 8px; }}
    .metric span {{ color: var(--muted); font-size: 13px; }}
    .passed strong {{ color: var(--pass); }}
    .failed strong {{ color: var(--fail); }}
    .error strong {{ color: var(--error); }}
    .skipped strong {{ color: var(--skip); }}
    .section {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; margin-top: 18px; overflow: hidden; }}
    .section h2 {{ margin: 0; padding: 14px 16px; font-size: 18px; border-bottom: 1px solid var(--line); }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ padding: 10px 12px; border-bottom: 1px solid var(--line); vertical-align: top; text-align: left; font-size: 14px; }}
    th {{ background: var(--bg-lighter); color: #475569; }}
    tr:last-child td {{ border-bottom: 0; }}
    .badge {{ display: inline-block; min-width: 64px; padding: 3px 8px; border-radius: 999px; color: white; text-align: center; font-size: 12px; font-weight: 700; }}
    .badge.passed {{ background: var(--pass); }}
    .badge.failed {{ background: var(--fail); }}
    .badge.error {{ background: var(--error); }}
    .badge.skipped {{ background: var(--skip); }}
    details {{ margin-top: 8px; }}
    summary {{ cursor: pointer; color: var(--blue); }}
    pre {{ white-space: pre-wrap; word-break: break-word; background: #0f172a; color: #e5e7eb; padding: 12px; border-radius: 6px; max-height: 460px; overflow: auto; }}
    .console-log {{ max-height: 520px; overflow: auto; background: #0f172a; padding: 12px; font-family: Consolas, 'Microsoft YaHei', monospace; font-size: 12px; line-height: 1.5; }}
    .console-line {{ display: grid; grid-template-columns: 70px minmax(0, 1fr); gap: 10px; padding: 6px 8px; border-left: 3px solid #334155; border-radius: 6px; color: #dbe5f2; overflow-wrap: anywhere; }}
    .console-line + .console-line {{ margin-top: 4px; }}
    .console-level {{ justify-self: start; padding: 1px 7px; border-radius: 999px; background: #1e293b; color: #cbd5e1; font-weight: 700; }}
    .console-pass {{ border-left-color: #22c55e; background: rgba(20, 83, 45, 0.18); }}
    .console-pass .console-level {{ background: rgba(34, 197, 94, 0.16); color: #86efac; }}
    .console-fail {{ border-left-color: #ef4444; background: rgba(127, 29, 29, 0.24); }}
    .console-fail .console-level {{ background: rgba(239, 68, 68, 0.18); color: #fecaca; }}
    .console-warn {{ border-left-color: #f59e0b; background: rgba(120, 53, 15, 0.18); }}
    .console-warn .console-level {{ background: rgba(245, 158, 11, 0.16); color: #fde68a; }}
    .console-click {{ border-left-color: #38bdf8; }}
    .console-click .console-level {{ background: rgba(56, 189, 248, 0.14); color: #bae6fd; }}
    .console-start {{ border-left-color: #818cf8; }}
    .console-start .console-level {{ background: rgba(129, 140, 248, 0.16); color: #c7d2fe; }}
    .trace-table td {{ font-size: 13px; }}
    .trace-kind {{ width: 90px; }}
    .trace-title {{ font-weight: 700; color: #0f172a; font-size: 15px; }}
    .trace-detail {{ margin-top: 4px; color: var(--muted); font-size: 12px; overflow-wrap: anywhere; }}
    .trace-badge {{ display: inline-block; min-width: 64px; padding: 3px 8px; border-radius: 999px; text-align: center; font-size: 12px; font-weight: 700; }}
    .trace-pass {{ background: rgba(34, 197, 94, 0.14); color: #15803d; }}
    .trace-fail {{ background: rgba(239, 68, 68, 0.14); color: #b91c1c; }}
    .trace-pending {{ background: rgba(56, 189, 248, 0.16); color: #0369a1; }}
    .trace-chip {{ display: inline-block; margin: 2px 4px 2px 0; padding: 2px 7px; border-radius: 999px; background: #f1f5f9; color: #475569; font-size: 12px; }}
    .env {{ display: grid; grid-template-columns: minmax(260px, 0.24fr) minmax(0, 1fr); gap: 0; }}
    .env div {{ min-width: 0; padding: 9px 12px; border-bottom: 1px solid var(--line); overflow-wrap: anywhere; word-break: break-word; }}
    .env div:nth-child(odd) {{ color: var(--muted); background: var(--bg-lighter); font-family: Consolas, 'Microsoft YaHei', monospace; }}
    @media (max-width: 960px) {{ .summary {{ grid-template-columns: repeat(2, 1fr); }} main, header {{ padding-left: 16px; padding-right: 16px; }} }}
  </style>
</head>
<body>
  <header>
    <h1>产品中心自动化测试报告</h1>
    <div class="meta">状态：{escape(status)} · 生成时间：{escape(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))}</div>
  </header>
  <main>
    <div class="summary">
      <div class="metric"><strong>{total}</strong><span>总用例</span></div>
      <div class="metric passed"><strong>{passed}</strong><span>通过</span></div>
      <div class="metric failed"><strong>{failures}</strong><span>失败</span></div>
      <div class="metric error"><strong>{errors}</strong><span>错误</span></div>
      <div class="metric skipped"><strong>{skipped}</strong><span>跳过</span></div>
      <div class="metric"><strong>{duration:.1f}s</strong><span>总耗时</span></div>
    </div>

    <section class="section">
      <h2>用例明细</h2>
      {build_records_table(records)}
    </section>

    <section class="section">
      <h2>运行环境</h2>
      <div class="env">
        {env_row("Python", sys.version.split()[0])}
        {env_row("Platform", platform.platform())}
        {env_row("Working Directory", os.getcwd())}
        {env_row("APPIUM_SERVER_URL", os.getenv("APPIUM_SERVER_URL", "http://127.0.0.1:4725/wd/hub"))}
        {env_row("DEVICE_NAME", os.getenv("DEVICE_NAME", "Android"))}
        {env_row("DEVICE_UDID", os.getenv("DEVICE_UDID", ""))}
        {env_row("APPIUM_SYSTEM_PORT", os.getenv("APPIUM_SYSTEM_PORT", ""))}
        {env_row("PRODUCT_CENTER_RUN_MODE", os.getenv("PRODUCT_CENTER_RUN_MODE", "full"))}
        {env_row("CHANNEL_JUMP_MAX_CASES", os.getenv("CHANNEL_JUMP_MAX_CASES", "0"))}
        {env_row("FEATURED_PRODUCT_MAX_CASES", os.getenv("FEATURED_PRODUCT_MAX_CASES", "0"))}
        {env_row("FEATURED_PRODUCT_START_AT", os.getenv("FEATURED_PRODUCT_START_AT", ""))}
        {env_row("FEATURED_PRODUCT_END_AT", os.getenv("FEATURED_PRODUCT_END_AT", ""))}
        {env_row("FEATURED_PRODUCT_COUNTRIES", os.getenv("FEATURED_PRODUCT_COUNTRIES", ""))}
        {env_row("FEATURED_PRODUCT_CHANNELS", os.getenv("FEATURED_PRODUCT_CHANNELS", ""))}
        {env_row("FEATURED_PRODUCTS", os.getenv("FEATURED_PRODUCTS", ""))}
        {env_row("RESET_EXTERNAL_APPS_BEFORE_PRODUCT_JUMP", os.getenv("RESET_EXTERNAL_APPS_BEFORE_PRODUCT_JUMP", "0"))}
        {env_row("RELAXED_EXTERNAL_BROWSER_CHECK", os.getenv("RELAXED_EXTERNAL_BROWSER_CHECK", "0"))}
        {env_row("STRICT_OFFICIAL_PRODUCT_URL", os.getenv("STRICT_OFFICIAL_PRODUCT_URL", "0"))}
        {env_row("STRICT_PRODUCT_DESTINATION", os.getenv("STRICT_PRODUCT_DESTINATION", "0"))}
        {env_row("PRODUCT_TEXT_FALLBACK", os.getenv("PRODUCT_TEXT_FALLBACK", "0"))}
        {env_row("HARD_RESET_AFTER_JUMP", os.getenv("HARD_RESET_AFTER_JUMP", "0"))}
      </div>
    </section>

    <section class="section">
      <h2>跳转结果总览</h2>
      {build_action_trace(stdout_text)}
    </section>

    <section class="section">
      <h2>控制台输出</h2>
      {build_console_output(stdout_text)}
    </section>
    {build_stderr_section(stderr_text)}
  </main>
</body>
</html>
"""


def build_records_table(records):
    if not records:
        return "<p style='padding: 16px; margin: 0;'>没有可展示的用例记录。</p>"

    rows = []
    for record in records:
        detail = record["traceback"] or record["message"]
        rows.append(
            "<tr>"
            f"<td><span class='badge {escape(record['status'])}'>{escape(record['status'].upper())}</span></td>"
            f"<td>{escape(record['name'])}"
            + (f"<div style='color:#64748b;margin-top:4px'>父用例：{escape(record['parent'])}</div>" if record["parent"] else "")
            + "</td>"
            f"<td>{record['duration']:.1f}s</td>"
            f"<td>{build_detail(detail)}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>状态</th><th>用例</th><th>耗时</th><th>详情</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def build_action_trace(stdout_text):
    rows = merge_jump_events(parse_jump_event(line) for line in str(stdout_text or "").splitlines() if line.strip())

    if not rows:
        return "<p style='padding: 16px; margin: 0;'>没有捕获到店铺或产品跳转结果。</p>"

    html_rows = []
    for item in rows:
        subject = item.get("product") or item.get("channel") or item.get("title") or "跳转项"
        chips = "".join(
            f"<span class='trace-chip'>{escape(label)}：{escape(value)}</span>"
            for label, value in [
                ("国家/地区", item.get("country")),
                ("渠道/店铺", item.get("channel")),
            ]
            if value
        )
        matched = f"<div class='trace-detail'>命中：{escape(item['matched'])}</div>" if item.get("matched") else ""
        destination = item.get("destination") or "目标链接/intent 已命中，等待跳转结果"
        html_rows.append(
            "<tr>"
            f"<td class='trace-kind'><span class='trace-badge trace-{escape(item['status'])}'>{escape(item['label'])}</span></td>"
            f"<td><div class='trace-title'>{escape(subject)}</div>{chips}<div class='trace-detail'>跳转结果：{escape(destination)}</div>{matched}</td>"
            "</tr>"
        )
    return (
        "<table class='trace-table'><thead><tr><th>状态</th><th>产品/店铺与结果</th></tr></thead>"
        f"<tbody>{''.join(html_rows)}</tbody></table>"
    )


def merge_jump_events(events):
    rows = []
    for event in (item for item in events if item):
        existing = find_jump_row(rows, event)
        if existing:
            existing.update(
                {
                    "status": event["status"] if not (event["status"] == "pending" and existing["status"] == "pass") else existing["status"],
                    "label": existing["label"] if event["status"] == "pending" and existing.get("label") else event["label"],
                    "country": existing.get("country") or event.get("country", ""),
                    "channel": existing.get("channel") or event.get("channel", ""),
                    "product": existing.get("product") or event.get("product", ""),
                    "title": existing.get("title") or event.get("title", ""),
                    "matched": existing.get("matched") or event.get("matched", ""),
                    "destination": event.get("destination") or existing.get("destination", ""),
                }
            )
        else:
            rows.append(event)
    return rows


def find_jump_row(rows, event):
    for row in rows:
        if row.get("key") == event.get("key") and row.get("status") != "pass":
            return row
    for row in reversed(rows):
        same_product = event.get("product") and row.get("product") == event.get("product")
        same_channel = not event.get("product") and event.get("channel") and row.get("channel") == event.get("channel")
        if (same_product or same_channel) and row.get("status") != "pass":
            return row
    return None


def parse_jump_event(line):
    text = re.sub(r"\s+", " ", str(line or "")).strip()
    if not text or re.search(r"当前在外部页面|常规返回无效|尝试返回|切回被测 App|已回到产品中心|恢复|重试|未生效", text):
        return None

    match = re.search(r"^(.+?)\s+链接/intent 目标校验通过：命中\s+(.+)$", text)
    if match:
        parts = split_jump_subject(match.group(1))
        return jump_event("pending", "目标已命中", parts, matched=match.group(2))

    match = re.search(r"^(.+?)\s+跳转成功：(.+)$", text)
    if match:
        parts = split_jump_subject(match.group(1))
        return jump_event("pass", "跳转成功", parts, destination=match.group(2))

    match = re.search(r"^点击\s+(.+?)\s+后没有跳转到(.+)$", text)
    if match:
        parts = split_jump_subject(match.group(1))
        return jump_event("fail", "未跳转", parts, destination=f"没有跳转到{match.group(2)}")

    match = re.search(r"^(.+?)\s+跳转失败：(.+)$", text)
    if match:
        parts = split_jump_subject(match.group(1))
        return jump_event("fail", "跳转失败", parts, destination=match.group(2))

    return None


def split_jump_subject(subject):
    text = re.sub(r"\s+", " ", str(subject or "")).strip()
    countries, channels = known_jump_terms()
    country = ""
    rest = text
    for item in sorted(countries, key=len, reverse=True):
        if rest == item or rest.startswith(f"{item} "):
            country = item
            rest = rest[len(item) :].strip()
            break

    if " / " in rest:
        channel, product = [part.strip() for part in rest.split(" / ", 1)]
        return {"country": country, "channel": channel, "product": product, "raw": text}

    for item in sorted(channels, key=len, reverse=True):
        if rest == item or rest.startswith(f"{item} "):
            return {"country": country, "channel": item, "product": rest[len(item) :].strip(), "raw": text}

    return {"country": country, "channel": "", "product": rest, "raw": text}


def known_jump_terms():
    countries = []
    channels = ["本地经销商", "Amazon", "AliExpress", "淘宝", "JD"]
    try:
        from product_center_config import ALL_COUNTRIES, COUNTRY_CHANNELS

        countries = list(ALL_COUNTRIES)
        channels.extend(channel for values in COUNTRY_CHANNELS.values() for channel in values)
    except Exception:
        countries = ["中国", "美国", "加拿大", "墨西哥", "英国", "德国", "法国", "日本", "其他地区"]
    return list(dict.fromkeys(countries)), list(dict.fromkeys(channels))


def jump_event(status, label, parts, matched="", destination=""):
    return {
        "key": "|".join([parts.get("country", ""), parts.get("channel", ""), parts.get("product") or parts.get("raw", "")]),
        "status": status,
        "label": label,
        "country": parts.get("country", ""),
        "channel": parts.get("channel", ""),
        "product": parts.get("product", ""),
        "title": parts.get("product") or parts.get("channel") or parts.get("raw", ""),
        "matched": matched,
        "destination": destination,
    }


def build_legacy_action_trace(stdout_text):
    rows = []
    for line in (line for line in str(stdout_text or "").splitlines() if line.strip()):
        item = parse_action_trace_line(line)
        if item:
            rows.append(item)

    if not rows:
        return "<p style='padding: 16px; margin: 0;'>没有捕获到点击或跳转结果。</p>"

    html_rows = []
    for index, item in enumerate(rows, 1):
        detail = f"<div class='trace-detail'>{escape(item['detail'])}</div>" if item["detail"] else ""
        html_rows.append(
            "<tr>"
            f"<td class='trace-index'>{index}</td>"
            f"<td class='trace-kind'><span class='trace-badge trace-{escape(item['status'])}'>{escape(item['label'])}</span></td>"
            f"<td><div class='trace-title'>{escape(item['title'])}</div>{detail}</td>"
            "</tr>"
        )
    return (
        "<table class='trace-table'><thead><tr><th>#</th><th>类型</th><th>动作/结果</th></tr></thead>"
        f"<tbody>{''.join(html_rows)}</tbody></table>"
    )


def parse_action_trace_line(line):
    text = re.sub(r"\s+", " ", str(line or "")).strip()
    if not text:
        return None

    match = re.search(r"点击成功：(.+?)（(.+?)）", text)
    if match:
        return {"status": "pass", "label": "点击成功", "title": match.group(1), "detail": match.group(2)}

    match = re.search(r"点击未生效，继续重试：(.+?)（(.+?)）", text)
    if match:
        return {"status": "warn", "label": "未生效", "title": match.group(1), "detail": match.group(2)}

    match = re.search(r"点击异常，继续重试：(.+?)（(.+?)）：(.+)", text)
    if match:
        return {
            "status": "fail",
            "label": "点击异常",
            "title": match.group(1),
            "detail": f"{match.group(2)}：{match.group(3)}",
        }

    match = re.search(r"Flutter 语义定位：(.+?)(?: content-desc=(.*?))?(?: bounds=(.+))?$", text)
    if match:
        details = [f"content-desc={match.group(2)}" if match.group(2) else "", f"bounds={match.group(3)}" if match.group(3) else ""]
        return {"status": "click", "label": "定位", "title": match.group(1), "detail": " · ".join(item for item in details if item)}

    match = re.search(r"^(.+?) bounds=(.+)$", text)
    if match and not re.search(r"^本次|^当前", match.group(1)):
        return {"status": "click", "label": "候选区域", "title": match.group(1), "detail": f"bounds={match.group(2)}"}

    if re.search(r"链接/intent 目标校验通过|跳转成功|已打开目标|已确认|已选择国家|已回到产品中心", text):
        return {"status": "pass", "label": "结果通过", "title": text, "detail": ""}

    if re.search(r"当前在外部页面|常规返回无效|尝试返回|恢复|重试|未生效", text):
        return {"status": "warn", "label": "恢复处理", "title": text, "detail": ""}

    if re.search(r"失败|异常|错误|未命中|Traceback|AssertionError|Error|ERROR", text):
        return {"status": "fail", "label": "结果失败", "title": text, "detail": ""}

    return None


def build_console_output(stdout_text):
    lines = [line for line in str(stdout_text or "").splitlines() if line.strip()]
    if not lines:
        return "<div class='console-log'><div class='console-line'><span class='console-level'>信息</span><span>没有控制台输出。</span></div></div>"

    return "<div class='console-log'>" + "".join(build_console_line(line) for line in lines) + "</div>"


def build_console_line(line):
    level, kind = classify_console_line(line)
    return (
        f"<div class='console-line console-{kind}'>"
        f"<span class='console-level'>{escape(level)}</span>"
        f"<span>{escape(line)}</span>"
        "</div>"
    )


def classify_console_line(line):
    text = str(line or "")
    if re.search(r"失败|异常|错误|未命中|Traceback|AssertionError|Error|ERROR|FAILED", text):
        return "错误", "fail"
    if re.search(r"跳过|skip|SKIP", text):
        return "跳过", "warn"
    if re.search(r"通过|成功|已打开目标|命中|已确认|已回到|已关闭|跳转成功|\\bok\\b|OK", text):
        return "通过", "pass"
    if re.search(r"点击|坐标|Flutter|content-desc|bounds=", text):
        return "点击", "click"
    if re.search(r"开始测试|开始配置|启动命令|工作目录|设备参数|当前为|断点开始|断点结束|^test_", text):
        return "开始", "start"
    if re.search(r"恢复|重试|返回|重建|重置|外部页面|未生效", text):
        return "恢复", "warn"
    return "信息", "info"


def build_detail(detail):
    if not detail:
        return ""
    return f"<details><summary>查看详情</summary><pre>{escape(detail)}</pre></details>"


def build_stderr_section(stderr_text):
    if not stderr_text:
        return ""
    return f"<section class='section'><h2>错误输出</h2><pre>{escape(stderr_text)}</pre></section>"


def env_row(label, value):
    return f"<div>{escape(label)}</div><div>{escape(value or '-') }</div>"


def escape(value):
    return html.escape(str(value or ""), quote=True)
