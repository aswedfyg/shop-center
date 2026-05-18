# -*- coding: utf-8 -*-

import argparse
import ast
import html
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
import urllib.parse
import webbrowser
from datetime import datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from shared_styles import generate_css_variables


ROOT = Path(__file__).resolve().parent
REPORT_DIR = ROOT / "reports"
ENTRYPOINT = ROOT / "Untitled-1.py"


class RunState:
    def __init__(self):
        self.lock = threading.Lock()
        self.process = None
        self.processes = []
        self.logs = []
        self.started_at = None
        self.finished_at = None
        self.exit_code = None
        self.command = []
        self.env = {}

    def snapshot(self):
        with self.lock:
            now = datetime.now()
            running = any(item["process"].poll() is None for item in self.processes)
            devices = []
            for item in self.processes:
                process_running = item["process"].poll() is None
                start_time = item.get("start_time")
                end_time = item.get("end_time")
                duration_end = now if process_running else (end_time or now)
                devices.append(
                    {
                        "name": item["name"],
                        "udid": item["udid"],
                        "running": process_running,
                        "exitCode": item.get("exit_code"),
                        "ports": item.get("ports", {}),
                        "startedAt": start_time.strftime("%H:%M:%S") if start_time else "",
                        "finishedAt": end_time.strftime("%H:%M:%S") if end_time else "",
                        "durationSeconds": int((duration_end - start_time).total_seconds()) if start_time else 0,
                    }
                )
            return {
                "running": running,
                "startedAt": self.started_at,
                "finishedAt": self.finished_at,
                "exitCode": self.exit_code,
                "command": self.command,
                "env": self.env,
                "devices": devices,
                "logCount": len(self.logs),
                "latestReport": latest_report_name(),
            }

    def append_log(self, line):
        with self.lock:
            self.logs.append({"time": datetime.now().strftime("%H:%M:%S"), "text": line})


STATE = RunState()


class SafeConstEvaluator:
    def __init__(self):
        self.values = {}

    def eval(self, node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.List):
            return [self.eval(item) for item in node.elts]
        if isinstance(node, ast.Tuple):
            return tuple(self.eval(item) for item in node.elts)
        if isinstance(node, ast.Set):
            return {self.eval(item) for item in node.elts}
        if isinstance(node, ast.Dict):
            return {self.eval(key): self.eval(value) for key, value in zip(node.keys, node.values)}
        if isinstance(node, ast.Name):
            return self.values[node.id]
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            return self.eval(node.left) + self.eval(node.right)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -self.eval(node.operand)
        raise ValueError(type(node).__name__)

    def assign(self, name, node):
        try:
            self.values[name] = self.eval(node)
        except Exception:
            return


def load_config_snapshot():
    config_path = ROOT / "product_center_config.py"
    flow_path = ROOT / "product_center_flow.py"
    evaluator = SafeConstEvaluator()
    if config_path.exists():
        tree = ast.parse(config_path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        evaluator.assign(target.id, node.value)

    tests = []
    if flow_path.exists():
        flow_tree = ast.parse(flow_path.read_text(encoding="utf-8"))
        for node in ast.walk(flow_tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                tests.append(node.name)

    country_channels = evaluator.values.get("COUNTRY_CHANNELS", {})
    countries = evaluator.values.get("ALL_COUNTRIES") or list(country_channels)
    products = evaluator.values.get("FULL_FEATURED_PRODUCTS", [])

    devices = discover_android_devices()
    online_device = next((item for item in devices if item.get("state") == "device"), None)
    fallback_device_name = (online_device or devices[0]).get("name") if devices else "Android"

    return {
        "tests": tests,
        "countries": countries,
        "channelsByCountry": country_channels,
        "channels": sorted({channel for values in country_channels.values() for channel in values}),
        "products": products,
        "reports": report_items(),
        "devices": devices,
        "defaults": {
            "appiumServerUrl": os.getenv("APPIUM_SERVER_URL", "http://127.0.0.1:4725/wd/hub"),
            "deviceName": os.getenv("DEVICE_NAME") or fallback_device_name,
            "deviceUdid": os.getenv("DEVICE_UDID", ""),
            "mode": os.getenv("PRODUCT_CENTER_RUN_MODE", "full"),
        },
    }


def discover_android_devices():
    adb_path = os.getenv("ADB_PATH", "adb")
    try:
        result = subprocess.run(
            [adb_path, "devices", "-l"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
    except Exception:
        return []

    devices = []
    for raw_line in (result.stdout or "").splitlines()[1:]:
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        serial, state = parts[0], parts[1]
        meta = {}
        for token in parts[2:]:
            if ":" in token:
                key, value = token.split(":", 1)
                meta[key] = value
        model = meta.get("model", "").replace("_", " ")
        name = model or meta.get("product") or serial
        devices.append(
            {
                "id": serial,
                "udid": serial,
                "name": name,
                "state": state,
                "model": model,
                "product": meta.get("product", ""),
                "transportId": meta.get("transport_id", ""),
            }
        )
    return devices


def find_available_port(host, preferred):
    for port in range(preferred, preferred + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, port))
            except OSError:
                continue
            return port
    raise RuntimeError(f"No available port from {preferred} to {preferred + 49}")


def allocate_unique_port(host, preferred, reserved):
    port = preferred
    while True:
        port = find_available_port(host, port)
        if port not in reserved:
            reserved.add(port)
            return port
        port += 1


def latest_report_name():
    latest = REPORT_DIR / "latest_product_center_report.html"
    if latest.exists():
        return latest.name
    items = report_items()
    return items[0]["name"] if items else ""


def latest_failure_breakpoint():
    latest = REPORT_DIR / "latest_product_center_report.html"
    if not latest.exists():
        return {"ok": False, "message": "还没有最新报告，无法自动填写断点"}

    text = html.unescape(latest.read_text(encoding="utf-8", errors="replace"))
    pattern = re.compile(r"\(country='([^']+)', channel='([^']+)', product='([^']+)'\)")
    match = pattern.search(text)
    if match:
        country, channel, product = (item.strip() for item in match.groups())
        breakpoint = "|".join([country, channel, product])
        return {
            "ok": True,
            "breakpoint": breakpoint,
            "country": country,
            "channel": channel,
            "product": product,
            "report": latest.name,
        }

    partial = re.search(r"\(country='([^']+)', channel='([^']+)'\)", text)
    if partial:
        country, channel = (item.strip() for item in partial.groups())
        return {
            "ok": False,
            "message": f"最新失败是渠道用例：{country}|{channel}，不是三段产品断点",
            "country": country,
            "channel": channel,
            "report": latest.name,
        }

    return {"ok": False, "message": "最新报告中没有可识别的产品断点", "report": latest.name}


def report_items():
    if not REPORT_DIR.exists():
        return []
    files = sorted(REPORT_DIR.glob("*.html"), key=lambda path: path.stat().st_mtime, reverse=True)
    return [
        {
            "name": path.name,
            "size": path.stat().st_size,
            "mtime": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            "version": str(path.stat().st_mtime_ns),
            "url": f"/reports/{urllib.parse.quote(path.name)}",
        }
        for path in files
    ]


def normalize_list(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def normalize_devices(payload):
    raw_devices = payload.get("devices")
    devices = []
    seen = set()
    if isinstance(raw_devices, list):
        for index, item in enumerate(raw_devices):
            if isinstance(item, dict):
                udid = str(item.get("udid") or item.get("id") or "").strip()
                name = str(item.get("name") or item.get("model") or udid or f"Android-{index + 1}").strip()
                key = udid or name
                if key and key not in seen:
                    seen.add(key)
                    devices.append({"name": name, "udid": udid})
            else:
                udid = str(item).strip()
                if udid and udid not in seen:
                    seen.add(udid)
                    devices.append({"name": udid, "udid": udid})

    if not devices:
        udid = str(payload.get("deviceUdid") or "").strip()
        name = str(payload.get("deviceName") or udid or "Android").strip()
        devices.append({"name": name, "udid": udid})
    return devices


def start_run(payload):
    with STATE.lock:
        if any(item["process"].poll() is None for item in STATE.processes):
            return False, "已有测试正在运行"

        base_env = os.environ.copy()
        base_env["PYTHONUTF8"] = "1"
        base_env["PYTHONIOENCODING"] = "utf-8"
        base_env["PYTHONUNBUFFERED"] = "1"

        env_updates = {
            "PRODUCT_CENTER_RUN_MODE": payload.get("mode", "full"),
            "APPIUM_SERVER_URL": payload.get("appiumServerUrl", "").strip(),
            "CHANNEL_JUMP_MAX_CASES": str(payload.get("channelMax") or 0),
            "FEATURED_PRODUCT_MAX_CASES": str(payload.get("productMax") or 0),
            "FEATURED_PRODUCT_START_AT": payload.get("startAt", "").strip(),
            "FEATURED_PRODUCT_END_AT": payload.get("endAt", "").strip(),
            "RELAXED_EXTERNAL_BROWSER_CHECK": "1" if payload.get("relaxedBrowser") else "0",
            "STRICT_OFFICIAL_PRODUCT_URL": "1" if payload.get("strictOfficialUrl") else "0",
            "STRICT_PRODUCT_DESTINATION": "1" if payload.get("strictProductDestination") else "0",
            "PRODUCT_TEXT_FALLBACK": "1" if payload.get("productTextFallback") else "0",
            "HARD_RESET_AFTER_JUMP": "1" if payload.get("hardReset") else "0",
        }

        list_updates = {
            "FEATURED_PRODUCT_COUNTRIES": normalize_list(payload.get("countries")),
            "FEATURED_PRODUCT_CHANNELS": normalize_list(payload.get("channels")),
            "FEATURED_PRODUCTS": normalize_list(payload.get("products")),
        }

        for key, value in env_updates.items():
            if value:
                base_env[key] = value
            else:
                base_env.pop(key, None)
        for key, values in list_updates.items():
            if values:
                base_env[key] = ",".join(values)
            else:
                base_env.pop(key, None)

        tests = normalize_list(payload.get("tests"))
        command = [sys.executable, "-u", str(ENTRYPOINT), *tests]
        devices = normalize_devices(payload)

        STATE.logs = []
        STATE.started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        STATE.finished_at = None
        STATE.exit_code = None
        STATE.command = [command]
        STATE.processes = []
        STATE.env = {
            key: base_env.get(key, "")
            for key in [
                "PRODUCT_CENTER_RUN_MODE",
                "APPIUM_SERVER_URL",
                "FEATURED_PRODUCT_COUNTRIES",
                "FEATURED_PRODUCT_CHANNELS",
                "FEATURED_PRODUCTS",
                "CHANNEL_JUMP_MAX_CASES",
                "FEATURED_PRODUCT_MAX_CASES",
                "FEATURED_PRODUCT_START_AT",
                "FEATURED_PRODUCT_END_AT",
                "RELAXED_EXTERNAL_BROWSER_CHECK",
                "STRICT_OFFICIAL_PRODUCT_URL",
                "STRICT_PRODUCT_DESTINATION",
                "PRODUCT_TEXT_FALLBACK",
                "HARD_RESET_AFTER_JUMP",
            ]
        }
        STATE.env["DEVICES"] = ", ".join(device["udid"] or device["name"] for device in devices)

        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        port_probe_host = "127.0.0.1"
        reserved_ports = set()
        for index, device in enumerate(devices):
            env = base_env.copy()
            env["DEVICE_NAME"] = device["name"] or device["udid"] or "Android"
            if device["udid"]:
                env["DEVICE_UDID"] = device["udid"]
            else:
                env.pop("DEVICE_UDID", None)
            if len(devices) > 1 or device["udid"]:
                env["APPIUM_SYSTEM_PORT"] = str(allocate_unique_port(port_probe_host, 8200 + index * 10, reserved_ports))
                env["APPIUM_CHROMEDRIVER_PORT"] = str(allocate_unique_port(port_probe_host, 9515 + index * 10, reserved_ports))
                env["APPIUM_MJPEG_SERVER_PORT"] = str(allocate_unique_port(port_probe_host, 7810 + index * 10, reserved_ports))

            process = subprocess.Popen(
                command,
                cwd=ROOT,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=creationflags,
            )
            run_info = {
                "process": process,
                "command": command,
                "env": env,
                "name": env["DEVICE_NAME"],
                "udid": env.get("DEVICE_UDID", ""),
                "exit_code": None,
                "start_time": datetime.now(),
                "end_time": None,
                "ports": {
                    "system": env.get("APPIUM_SYSTEM_PORT", ""),
                    "chromedriver": env.get("APPIUM_CHROMEDRIVER_PORT", ""),
                    "mjpeg": env.get("APPIUM_MJPEG_SERVER_PORT", ""),
                },
            }
            STATE.processes.append(run_info)

        STATE.process = STATE.processes[0]["process"] if STATE.processes else None

    for run_info in STATE.processes:
        threading.Thread(target=watch_process, args=(run_info,), daemon=True).start()
    return True, f"测试已启动：{len(devices)} 台设备"


def format_command(command):
    return " ".join(f'"{part}"' if " " in part else part for part in command)


def watch_process(run_info):
    process = run_info["process"]
    device_label = run_info["udid"] or run_info["name"]
    prefix = f"[{device_label}] "
    STATE.append_log(prefix + "启动命令：" + format_command(run_info["command"]))
    STATE.append_log(prefix + "工作目录：" + str(ROOT))
    STATE.append_log(
        prefix
        + "设备参数："
        + f"DEVICE_NAME={run_info['env'].get('DEVICE_NAME', '')}, "
        + f"DEVICE_UDID={run_info['env'].get('DEVICE_UDID', '') or '-'}, "
        + f"systemPort={run_info['env'].get('APPIUM_SYSTEM_PORT', '') or '-'}"
    )
    STATE.append_log(
        prefix
        + "运行范围："
        + f"mode={run_info['env'].get('PRODUCT_CENTER_RUN_MODE', '') or '-'}, "
        + f"countries={run_info['env'].get('FEATURED_PRODUCT_COUNTRIES', '') or '按模式默认'}, "
        + f"channels={run_info['env'].get('FEATURED_PRODUCT_CHANNELS', '') or '全部'}, "
        + f"products={run_info['env'].get('FEATURED_PRODUCTS', '') or '按模式默认'}, "
        + f"productMax={run_info['env'].get('FEATURED_PRODUCT_MAX_CASES', '') or '0'}"
    )
    if process.stdout:
        for line in process.stdout:
            STATE.append_log(prefix + line.rstrip("\n"))
    exit_code = process.wait()
    with STATE.lock:
        finished = datetime.now()
        run_info["exit_code"] = exit_code
        run_info["end_time"] = finished
        if STATE.processes and all(item["process"].poll() is not None for item in STATE.processes):
            exit_codes = [item.get("exit_code") for item in STATE.processes]
            STATE.exit_code = 0 if all(code == 0 for code in exit_codes) else 1
            STATE.finished_at = finished.strftime("%Y-%m-%d %H:%M:%S")
    STATE.append_log(prefix + f"测试进程结束，退出码：{exit_code}")


def stop_run():
    with STATE.lock:
        running = [item["process"] for item in STATE.processes if item["process"].poll() is None]
        if not running:
            return False, "当前没有运行中的测试"
        for process in running:
            process.terminate()
    STATE.append_log(f"已请求停止 {len(running)} 个测试进程")
    return True, "已请求停止"


class DashboardHandler(SimpleHTTPRequestHandler):
    server_version = "ProductCenterDashboard/1.0"

    def log_message(self, fmt, *args):
        return

    def write_response_body(self, content):
        try:
            self.wfile.write(content)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            return

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            return self.send_html(format_index_html())
        if parsed.path == "/api/config":
            return self.send_json(load_config_snapshot())
        if parsed.path == "/api/devices":
            return self.send_json({"devices": discover_android_devices()})
        if parsed.path == "/api/status":
            return self.send_json(STATE.snapshot())
        if parsed.path == "/api/reports":
            return self.send_json({"reports": report_items(), "latest": latest_report_name()})
        if parsed.path == "/api/failure-breakpoint":
            return self.send_json(latest_failure_breakpoint())
        if parsed.path == "/api/logs":
            query = urllib.parse.parse_qs(parsed.query)
            offset = int(query.get("offset", ["0"])[0] or 0)
            with STATE.lock:
                logs = STATE.logs[offset:]
                next_offset = len(STATE.logs)
            return self.send_json({"logs": logs, "nextOffset": next_offset})
        if parsed.path.startswith("/reports/"):
            return self.serve_report(parsed.path)
        return self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/run":
            payload = self.read_json()
            ok, message = start_run(payload)
            return self.send_json({"ok": ok, "message": message}, HTTPStatus.OK if ok else HTTPStatus.CONFLICT)
        if parsed.path == "/api/stop":
            ok, message = stop_run()
            return self.send_json({"ok": ok, "message": message}, HTTPStatus.OK if ok else HTTPStatus.CONFLICT)
        return self.send_error(HTTPStatus.NOT_FOUND)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        data = self.rfile.read(length).decode("utf-8")
        return json.loads(data or "{}")

    def serve_report(self, request_path):
        name = urllib.parse.unquote(request_path.removeprefix("/reports/"))
        path = (REPORT_DIR / name).resolve()
        try:
            path.relative_to(REPORT_DIR.resolve())
        except ValueError:
            return self.send_error(HTTPStatus.FORBIDDEN)
        if not path.exists() or path.suffix.lower() != ".html":
            return self.send_error(HTTPStatus.NOT_FOUND)
        content = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()
        self.write_response_body(content)

    def send_json(self, data, status=HTTPStatus.OK):
        content = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.write_response_body(content)

    def send_html(self, text, status=HTTPStatus.OK):
        content = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()
        self.write_response_body(content)


INDEX_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>产品中心自动化控制台</title>
  <style>
    {css_variables}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html {{ scroll-behavior: smooth; }}
    :root {{
      --header-height: 69px;
      --page-gap: 20px;
    }}
    body {{
      height: 100vh;
      min-height: 100vh;
      background: #f5f7fa;
      color: var(--text-primary);
      font-family: "Inter", "Segoe UI", "Microsoft YaHei", system-ui, sans-serif;
      line-height: 1.6;
      overflow: hidden;
    }}
    header {{
      background: #0f172a;
      color: var(--text-white);
      padding: 14px 24px;
      box-shadow: 0 2px 8px rgba(15, 23, 42, 0.12);
      position: sticky;
      top: 0;
      z-index: 100;
      border-bottom: 1px solid rgba(59, 130, 246, 0.1);
    }}
    .header-content {{
      max-width: 1920px;
      margin: 0 auto;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 20px;
    }}
    .brand {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .brand-icon {{
      width: 40px;
      height: 40px;
      background: #3b82f6;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 18px;
      font-weight: 700;
      color: white;
      flex-shrink: 0;
    }}
    .brand-text h1 {{
      font-size: 16px;
      font-weight: 700;
      color: #ffffff;
      line-height: 1.2;
    }}
    .brand-text small {{
      font-size: 11px;
      color: rgba(255, 255, 255, 0.5);
      margin-top: 1px;
      display: block;
    }}
    .status-indicator {{
      display: flex;
      align-items: center;
      gap: 8px;
      margin-left: auto;
    }}
    .status-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 7px 14px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      transition: all 0.3s ease;
    }}
    .status-badge.idle {{
      background: rgba(100, 116, 139, 0.15);
      color: #94a3b8;
    }}
    .status-badge.running {{
      background: rgba(6, 182, 212, 0.15);
      color: #06b6d4;
      animation: pulse 2s ease-in-out infinite;
    }}
    .status-badge.success {{
      background: rgba(34, 197, 94, 0.15);
      color: #22c55e;
    }}
    .status-badge.fail {{
      background: rgba(239, 68, 68, 0.15);
      color: #ef4444;
    }}
    .status-badge .dot {{
      width: 6px;
      height: 6px;
      border-radius: 50%;
    }}
    .status-badge.idle .dot {{ background: #94a3b8; }}
    .status-badge.running .dot {{ background: #06b6d4; animation: blink 1s ease-in-out infinite; }}
    .status-badge.success .dot {{ background: #22c55e; }}
    .status-badge.fail .dot {{ background: #ef4444; }}
    @keyframes pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.7; }} }}
    @keyframes blink {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.3; }} }}
    .main-container {{
      max-width: 1920px;
      margin: 0 auto;
      height: calc(100vh - var(--header-height));
      min-height: 0;
      padding: var(--page-gap);
      display: grid;
      grid-template-columns: minmax(360px, 400px) minmax(0, 1fr);
      gap: 20px;
      overflow: hidden;
    }}
    @media (max-width: 1240px) {{
      .main-container {{ grid-template-columns: 1fr; }}
    }}
    .sidebar {{
      display: flex;
      flex-direction: column;
      gap: 12px;
      align-self: start;
      min-width: 0;
      height: 100%;
      min-height: 0;
      overflow-y: auto;
      padding-right: 4px;
      scrollbar-width: thin;
      scrollbar-color: #cbd5e1 transparent;
    }}
    .sidebar::-webkit-scrollbar {{
      width: 6px;
    }}
    .sidebar::-webkit-scrollbar-track {{
      background: transparent;
    }}
    .sidebar::-webkit-scrollbar-thumb {{
      background: #cbd5e1;
      border-radius: 999px;
    }}
    .sidebar::-webkit-scrollbar-thumb:hover {{
      background: #94a3b8;
    }}
    main {{
      min-width: 0;
      min-height: 0;
      height: 100%;
      display: flex;
      flex-direction: column;
    }}
    .panel {{
      background: white;
      border-radius: 10px;
      box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
      overflow: hidden;
      border: 1px solid #e2e8f0;
      transition: all 0.2s ease;
      flex-shrink: 0;
      min-width: 0;
    }}
    .panel:hover {{
      box-shadow: 0 2px 6px rgba(15, 23, 42, 0.1);
    }}
    .panel-header {{
      padding: 12px 14px;
      background: #f8fafc;
      border-bottom: 1px solid #e2e8f0;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      min-width: 0;
    }}
    .panel-header h2 {{
      font-size: 13px;
      font-weight: 700;
      color: #0f172a;
      letter-spacing: 0.2px;
    }}
    .panel-body {{
      padding: 14px;
      min-width: 0;
    }}
    .config-section {{
      padding: 12px 0;
      border-top: 1px solid #eef2f7;
    }}
    .config-section:first-child {{
      padding-top: 0;
      border-top: 0;
    }}
    .config-section:last-child {{
      padding-bottom: 0;
    }}
    .section-title {{
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 10px;
      color: #0f172a;
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.2px;
    }}
    .section-title::before {{
      content: "";
      width: 3px;
      height: 14px;
      border-radius: 999px;
      background: #3b82f6;
      flex-shrink: 0;
    }}
    .section-note {{
      margin-top: -5px;
      margin-bottom: 10px;
      color: #94a3b8;
      font-size: 11px;
      line-height: 1.4;
    }}
    .form-group {{
      margin-bottom: 12px;
    }}
    .form-group:last-child {{ margin-bottom: 0; }}
    .form-label {{
      display: block;
      font-size: 12px;
      font-weight: 700;
      color: #0f172a;
      margin-bottom: 6px;
      letter-spacing: 0.1px;
      text-transform: uppercase;
    }}
    .form-control {{
      width: 100%;
      padding: 9px 11px;
      border: 1px solid #d4d8dc;
      border-radius: 6px;
      font-size: 13px;
      background: #ffffff;
      color: #0f172a;
      transition: all 0.2s ease;
      font-family: inherit;
    }}
    .form-control:hover {{
      border-color: #cbd5e1;
    }}
    .form-control:focus {{
      outline: none;
      border-color: #3b82f6;
      box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }}
    .form-control::placeholder {{ color: #cbd5e1; }}
    .form-control:disabled {{
      color: #94a3b8;
      background: #f8fafc;
      cursor: not-allowed;
    }}
    .selection-combo {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      align-items: stretch;
      overflow: hidden;
      border: 1px solid #d4d8dc;
      border-radius: 8px;
      background: #ffffff;
      transition: border-color 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
    }}
    .selection-combo:hover {{
      border-color: #94a3b8;
      background: #fbfdff;
    }}
    .selection-combo:focus-within,
    .selection-combo.expanded {{
      border-color: #3b82f6;
      box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }}
    .selection-main {{
      min-width: 0;
      padding: 8px 10px;
    }}
    .selection-chips {{
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 5px;
      min-height: 24px;
    }}
    .selection-chip {{
      max-width: 100%;
      padding: 3px 8px;
      border-radius: 999px;
      background: #eef6ff;
      color: #1d4ed8;
      border: 1px solid #bfdbfe;
      font-size: 11px;
      font-weight: 700;
      line-height: 1.4;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .selection-chip.more {{
      color: #475569;
      background: #f1f5f9;
      border-color: #e2e8f0;
    }}
    .selection-empty {{
      color: #94a3b8;
      font-size: 12px;
      font-weight: 600;
    }}
    .selection-input {{
      width: 100%;
      min-width: 0;
      margin-top: 5px;
      border: 0;
      outline: 0;
      background: transparent;
      color: #0f172a;
      font: inherit;
      font-size: 12px;
      line-height: 1.45;
    }}
    .selection-input::placeholder {{
      color: #cbd5e1;
    }}
    .selection-action {{
      width: 58px;
      border: 0;
      border-left: 1px solid #e2e8f0;
      background: #f8fafc;
      color: #2563eb;
      font-size: 12px;
      font-weight: 800;
      cursor: pointer;
      transition: background 0.2s ease, color 0.2s ease;
    }}
    .selection-action:hover {{
      background: #eff6ff;
      color: #1d4ed8;
    }}
    .selection-action:active {{
      background: #dbeafe;
    }}
    .selection-action:focus-visible {{
      outline: 2px solid #3b82f6;
      outline-offset: -2px;
    }}
    .number-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }}
    .number-card {{
      padding: 10px;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      background: #fbfdff;
      transition: border-color 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
    }}
    .number-card:hover {{
      border-color: #bfdbfe;
      background: #ffffff;
    }}
    .number-card:focus-within {{
      border-color: #3b82f6;
      box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
      background: #ffffff;
    }}
    .number-card .form-control {{
      height: 34px;
      padding: 6px 8px;
      font-weight: 700;
      border-color: #e2e8f0;
      background: #ffffff;
    }}
    .range-group {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      padding: 10px;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      background: #fbfdff;
    }}
    .range-field {{
      min-width: 0;
    }}
    .range-actions {{
      grid-column: 1 / -1;
      display: flex;
      gap: 8px;
    }}
    .range-actions .btn {{
      flex: 1;
    }}
    .btn {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 5px;
      padding: 10px 16px;
      border: none;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s ease;
      min-height: 36px;
      font-family: inherit;
    }}
    .btn:disabled {{
      opacity: 0.5;
      cursor: not-allowed;
    }}
    .btn:disabled:hover {{
      transform: none;
      box-shadow: none;
    }}
    .btn-primary {{
      background: #3b82f6;
      color: white;
      box-shadow: 0 2px 4px rgba(59, 130, 246, 0.2);
    }}
    .btn-primary:hover:not(:disabled) {{
      background: #2563eb;
      box-shadow: 0 4px 8px rgba(59, 130, 246, 0.3);
      transform: translateY(-1px);
    }}
    .btn-primary:active:not(:disabled) {{ transform: translateY(0); }}
    .btn-danger {{
      background: #ef4444;
      color: white;
      box-shadow: 0 2px 4px rgba(239, 68, 68, 0.2);
    }}
    .btn-danger:hover:not(:disabled) {{
      background: #dc2626;
      box-shadow: 0 4px 8px rgba(239, 68, 68, 0.3);
      transform: translateY(-1px);
    }}
    .btn-danger:active:not(:disabled) {{ transform: translateY(0); }}
    .btn-secondary {{
      background: #f1f5f9;
      color: #0f172a;
      border: 1px solid #d4d8dc;
    }}
    .btn-secondary:hover:not(:disabled) {{
      background: #e2e8f0;
      border-color: #cbd5e1;
    }}
    .btn-sm {{
      padding: 7px 12px;
      font-size: 12px;
      min-height: 32px;
    }}
    .btn-group {{
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
    }}
    .btn-group .btn {{ flex: 1; min-width: 0; }}
    .device-summary {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
      margin-bottom: 12px;
    }}
    .device-summary-item {{
      padding: 10px 8px;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      background: #f8fafc;
      min-width: 0;
      transition: all 0.2s ease;
      text-align: center;
    }}
    .device-summary-item:hover {{
      border-color: #3b82f6;
      background: #eef7ff;
    }}
    .device-summary-item strong {{
      display: block;
      font-size: 18px;
      line-height: 1;
      color: #0f172a;
      margin-bottom: 3px;
    }}
    .device-summary-item span {{
      font-size: 10px;
      color: #64748b;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.1px;
    }}
    .device-grid {{
      display: flex;
      flex-direction: column;
      gap: 8px;
      max-height: 280px;
      overflow-y: auto;
      padding-right: 2px;
    }}
    .device-grid::-webkit-scrollbar {{
      width: 6px;
    }}
    .device-grid::-webkit-scrollbar-track {{
      background: transparent;
    }}
    .device-grid::-webkit-scrollbar-thumb {{
      background: #cbd5e1;
      border-radius: 3px;
    }}
    .device-grid::-webkit-scrollbar-thumb:hover {{
      background: #94a3b8;
    }}
    .device-card {{
      display: grid;
      grid-template-columns: auto minmax(0, 1fr) auto;
      align-items: start;
      gap: 10px;
      padding: 10px;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.2s ease;
      background: #ffffff;
    }}
    .device-card:hover {{
      border-color: #3b82f6;
      background: #f0f7ff;
      box-shadow: 0 2px 4px rgba(59, 130, 246, 0.1);
    }}
    .device-card.selected,
    .device-card:has(input:checked) {{
      border-color: #3b82f6;
      background: #eef7ff;
      box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.08);
    }}
    .device-card.disabled {{
      opacity: 0.5;
      cursor: not-allowed;
    }}
    .device-card.disabled:hover {{
      border-color: #e2e8f0;
      background: #ffffff;
      box-shadow: none;
    }}
    .device-radio {{
      width: 18px;
      height: 18px;
      flex-shrink: 0;
      margin-top: 1px;
      cursor: pointer;
      accent-color: #3b82f6;
    }}
    .device-info {{
      flex: 1;
      min-width: 0;
    }}
    .device-name {{
      font-weight: 600;
      font-size: 13px;
      color: #0f172a;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .device-udid {{
      font-size: 11px;
      color: #94a3b8;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      margin-top: 2px;
    }}
    .device-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
      margin-top: 6px;
    }}
    .device-meta span {{
      max-width: 100%;
      padding: 2px 6px;
      border-radius: 3px;
      background: #f1f5f9;
      color: #64748b;
      font-size: 10px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .device-status {{
      padding: 4px 9px;
      border-radius: 4px;
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.3px;
    }}
    .device-status.online {{
      background: rgba(34, 197, 94, 0.12);
      color: #16a34a;
    }}
    .device-status.offline {{
      background: rgba(239, 68, 68, 0.12);
      color: #dc2626;
    }}
    .checkbox-list {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 6px;
      max-height: 280px;
      overflow-y: auto;
      padding-right: 2px;
    }}
    .checkbox-list::-webkit-scrollbar {{
      width: 6px;
    }}
    .checkbox-list::-webkit-scrollbar-track {{
      background: transparent;
    }}
    .checkbox-list::-webkit-scrollbar-thumb {{
      background: #cbd5e1;
      border-radius: 3px;
    }}
    .checkbox-list::-webkit-scrollbar-thumb:hover {{
      background: #94a3b8;
    }}
    .checkbox-item {{
      display: flex;
      align-items: flex-start;
      gap: 8px;
      padding: 10px;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.2s ease;
      background: #ffffff;
    }}
    .checkbox-item:hover {{
      border-color: #3b82f6;
      background: #f0f7ff;
    }}
    .checkbox-item:has(input:focus-visible) {{
      outline: 2px solid #3b82f6;
      outline-offset: 2px;
    }}
    .checkbox-item:has(input:checked) {{
      border-color: #3b82f6;
      background: #eef7ff;
    }}
    .checkbox-item:has(input:disabled) {{
      opacity: 0.55;
      cursor: not-allowed;
      background: #f8fafc;
    }}
    .checkbox-item input {{
      margin-top: 2px;
      flex-shrink: 0;
      cursor: pointer;
      accent-color: #3b82f6;
      width: 16px;
      height: 16px;
    }}
    .checkbox-content {{
      flex: 1;
      min-width: 0;
    }}
    .checkbox-title {{
      font-weight: 600;
      font-size: 12px;
      color: #0f172a;
    }}
    .checkbox-desc {{
      font-size: 11px;
      color: #94a3b8;
      margin-top: 2px;
      line-height: 1.4;
    }}
    .checkbox-code {{
      font-size: 10px;
      color: #94a3b8;
      font-family: "JetBrains Mono", "Consolas", monospace;
      margin-top: 3px;
      background: #f1f5f9;
      padding: 2px 5px;
      border-radius: 3px;
      display: inline-block;
    }}
    .picker-container {{
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      overflow: hidden;
      background: #ffffff;
      transition: all 0.2s ease;
    }}
    .picker-header {{
      padding: 10px 12px;
      cursor: pointer;
      font-size: 12px;
      font-weight: 600;
      color: #3b82f6;
      display: flex;
      align-items: center;
      justify-content: space-between;
      transition: all 0.2s ease;
    }}
    .picker-header:hover {{ background: #f8fafc; }}
    .picker-header::after {{
      content: "\\25BC";
      font-size: 9px;
      transition: transform 0.2s;
    }}
    .picker-header.expanded::after {{ transform: rotate(180deg); }}
    .picker-content {{
      display: none;
      margin-top: 8px;
      padding: 10px;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      background: #f8fafc;
    }}
    .picker-content.expanded {{ display: block; }}
    .selector-dropdown .checkbox-list {{
      max-height: 188px;
    }}
    .option-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
    }}
    .option-card {{
      min-height: 48px;
      align-items: center;
      border-radius: 8px;
      background: #ffffff;
    }}
    .preset-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
    }}
    .preset-btn {{
      min-height: 36px;
      padding: 8px 10px;
      border-radius: 999px;
      background: #f8fafc;
      border-color: #dbe3eb;
      white-space: nowrap;
    }}
    .preset-btn:hover:not(:disabled) {{
      background: #eff6ff;
      border-color: #bfdbfe;
      color: #1d4ed8;
    }}
    .preset-btn:active:not(:disabled) {{
      background: #dbeafe;
    }}
    .metrics-grid {{
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 12px;
      margin-bottom: 14px;
      flex-shrink: 0;
    }}
    @media (max-width: 1000px) {{
      .metrics-grid {{ grid-template-columns: repeat(2, 1fr); }}
    }}
    @media (max-width: 540px) {{
      .metrics-grid {{ grid-template-columns: 1fr; }}
    }}
    .metric-card {{
      background: white;
      border-radius: 8px;
      padding: 14px 16px;
      box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
      border: 1px solid #e2e8f0;
      transition: all 0.2s ease;
    }}
    .metric-card:hover {{
      box-shadow: 0 2px 6px rgba(15, 23, 42, 0.1);
      border-color: #3b82f6;
    }}
    .metric-value {{
      font-size: 22px;
      font-weight: 700;
      color: #0f172a;
      margin-bottom: 4px;
      min-height: 28px;
      overflow-wrap: break-word;
      word-break: break-all;
    }}
    .metric-label {{
      font-size: 11px;
      color: #94a3b8;
      text-transform: uppercase;
      letter-spacing: 0.3px;
      font-weight: 700;
    }}
    .metrics-summary {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 10px;
      margin-bottom: 14px;
      flex-shrink: 0;
    }}
    .device-pill {{
      display: grid;
      grid-template-columns: auto minmax(0, 1fr) auto;
      align-items: start;
      gap: 8px;
      padding: 10px 12px;
      background: white;
      border-radius: 8px;
      box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
      border: 1px solid #e2e8f0;
      transition: all 0.2s ease;
    }}
    .device-pill:hover {{
      box-shadow: 0 2px 6px rgba(15, 23, 42, 0.1);
      border-color: #3b82f6;
    }}
    .device-pill .status-dot {{
      width: 8px;
      height: 8px;
      border-radius: 50%;
      margin-top: 4px;
    }}
    .device-pill.running .status-dot {{ background: #06b6d4; animation: blink 1s ease-in-out infinite; }}
    .device-pill.success .status-dot {{ background: #22c55e; }}
    .device-pill.fail .status-dot {{ background: #ef4444; }}
    .device-pill.idle .status-dot {{ background: #94a3b8; }}
    .device-pill .device-name {{
      font-size: 13px;
      font-weight: 600;
      color: #0f172a;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .tabs-container {{
      background: white;
      border-radius: 10px;
      box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
      border: 1px solid #e2e8f0;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      flex: 1;
      min-height: 0;
    }}
    .tabs-header {{
      display: flex;
      gap: 4px;
      padding: 8px;
      background: #f8fafc;
      border-bottom: 1px solid #e2e8f0;
      flex-shrink: 0;
    }}
    .tab-btn {{
      flex: 1;
      padding: 8px 14px;
      border: none;
      background: transparent;
      border-radius: 7px;
      font-size: 13px;
      font-weight: 600;
      color: #64748b;
      cursor: pointer;
      transition: all 0.2s ease;
      min-height: 34px;
    }}
    .tab-btn:hover {{ color: #0f172a; background: #edf2f7; }}
    .tab-btn.active {{
      color: #1d4ed8;
      background: white;
      box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
    }}
    .tab-btn:focus-visible,
    .btn:focus-visible,
    .form-control:focus-visible {{
      outline: 2px solid #3b82f6;
      outline-offset: 1px;
    }}
    .tab-content {{
      padding: 0;
      flex: 1;
      min-height: 0;
      display: grid;
    }}
    .tab-view {{
      min-height: 0;
      height: 100%;
    }}
    .log-container {{
      height: 100%;
      min-height: 520px;
      overflow-y: auto;
      background: #0f172a;
      padding: 16px;
      font-family: "JetBrains Mono", "Consolas", monospace;
      font-size: 12px;
      line-height: 1.5;
      color: #cbd5e1;
      border-radius: 0 0 10px 10px;
      scrollbar-width: thin;
      scrollbar-color: #475569 #111827;
    }}
    .log-line {{
      display: grid;
      grid-template-columns: 68px 58px minmax(86px, 150px) minmax(0, 1fr);
      gap: 8px;
      align-items: start;
      padding: 6px 8px;
      border-left: 3px solid #334155;
      border-radius: 6px;
      background: rgba(15, 23, 42, 0.72);
    }}
    .log-line + .log-line {{ margin-top: 4px; }}
    .log-time {{ color: #94a3b8; }}
    .log-level {{
      justify-self: start;
      padding: 1px 7px;
      border-radius: 999px;
      background: #1e293b;
      color: #cbd5e1;
      font-weight: 700;
    }}
    .log-device {{
      color: #dbeafe;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .log-message {{
      min-width: 0;
      color: #dbe5f2;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      word-break: break-word;
    }}
    .log-pass {{ border-left-color: #22c55e; background: rgba(20, 83, 45, 0.18); }}
    .log-pass .log-level {{ background: rgba(34, 197, 94, 0.16); color: #86efac; }}
    .log-fail {{ border-left-color: #ef4444; background: rgba(127, 29, 29, 0.24); }}
    .log-fail .log-level {{ background: rgba(239, 68, 68, 0.18); color: #fecaca; }}
    .log-warn {{ border-left-color: #f59e0b; background: rgba(120, 53, 15, 0.18); }}
    .log-warn .log-level {{ background: rgba(245, 158, 11, 0.16); color: #fde68a; }}
    .log-click {{ border-left-color: #38bdf8; }}
    .log-click .log-level {{ background: rgba(56, 189, 248, 0.14); color: #bae6fd; }}
    .log-start {{ border-left-color: #818cf8; }}
    .log-start .log-level {{ background: rgba(129, 140, 248, 0.16); color: #c7d2fe; }}
    .log-container:empty::before {{
      content: "等待任务启动后输出日志";
      display: grid;
      min-height: 100%;
      place-items: center;
      color: #64748b;
      font-family: "Inter", "Segoe UI", "Microsoft YaHei", system-ui, sans-serif;
      font-size: 13px;
      font-weight: 600;
    }}
    .log-container::-webkit-scrollbar {{
      width: 6px;
    }}
    .log-container::-webkit-scrollbar-track {{
      background: #1e293b;
    }}
    .log-container::-webkit-scrollbar-thumb {{
      background: #475569;
      border-radius: 3px;
    }}
    .log-container::-webkit-scrollbar-thumb:hover {{
      background: #64748b;
    }}
    .trace-container {{
      height: 100%;
      min-height: 520px;
      overflow-y: auto;
      background: #ffffff;
      border-radius: 0 0 10px 10px;
      scrollbar-width: thin;
      scrollbar-color: #cbd5e1 transparent;
    }}
    .trace-container::-webkit-scrollbar {{
      width: 6px;
    }}
    .trace-container::-webkit-scrollbar-track {{
      background: transparent;
    }}
    .trace-container::-webkit-scrollbar-thumb {{
      background: #cbd5e1;
      border-radius: 3px;
    }}
    .trace-summary {{
      position: sticky;
      top: 0;
      z-index: 2;
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 8px;
      padding: 12px;
      background: #f8fafc;
      border-bottom: 1px solid #e2e8f0;
    }}
    .trace-stat {{
      min-width: 0;
      padding: 8px 10px;
      border: 1px solid #e2e8f0;
      border-radius: 7px;
      background: #ffffff;
    }}
    .trace-stat strong {{
      display: block;
      font-size: 18px;
      line-height: 1;
      color: #0f172a;
    }}
    .trace-stat span {{
      display: block;
      margin-top: 4px;
      font-size: 10px;
      color: #64748b;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.3px;
    }}
    .trace-list {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
      gap: 12px;
      padding: 12px;
    }}
    .trace-card {{
      min-width: 0;
      display: grid;
      grid-template-rows: auto 1fr auto;
      gap: 10px;
      padding: 14px;
      border: 1px solid #e2e8f0;
      border-left: 5px solid #94a3b8;
      border-radius: 8px;
      background: #ffffff;
      box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
    }}
    .trace-card-head {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 10px;
      align-items: start;
    }}
    .trace-time {{
      color: #64748b;
      font-size: 11px;
      font-family: "JetBrains Mono", "Consolas", monospace;
    }}
    .trace-device {{
      min-width: 0;
      color: #334155;
      font-size: 11px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .trace-title {{
      color: #0f172a;
      font-size: 16px;
      line-height: 1.35;
      font-weight: 700;
      overflow-wrap: anywhere;
    }}
    .trace-subtitle {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 6px;
    }}
    .trace-chip {{
      max-width: 100%;
      padding: 2px 7px;
      border-radius: 999px;
      background: #f1f5f9;
      color: #475569;
      font-size: 11px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .trace-detail {{
      min-width: 0;
      color: #64748b;
      font-size: 12px;
      overflow-wrap: anywhere;
    }}
    .trace-result {{
      padding: 10px;
      border-radius: 7px;
      background: rgba(241, 245, 249, 0.72);
      border: 1px solid #e2e8f0;
    }}
    .trace-result-label {{
      margin-bottom: 4px;
      color: #64748b;
      font-size: 10px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.3px;
    }}
    .trace-meta {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      min-width: 0;
    }}
    .trace-badge {{
      padding: 2px 7px;
      border-radius: 999px;
      font-size: 11px;
      font-weight: 700;
      white-space: nowrap;
      background: #f1f5f9;
      color: #475569;
    }}
    .trace-pass {{ border-left-color: #22c55e; background: #f7fef9; }}
    .trace-pass .trace-badge {{ background: rgba(34, 197, 94, 0.14); color: #15803d; }}
    .trace-fail {{ border-left-color: #ef4444; background: #fff7f7; }}
    .trace-fail .trace-badge {{ background: rgba(239, 68, 68, 0.14); color: #b91c1c; }}
    .trace-pending {{ border-left-color: #38bdf8; background: #f8fcff; }}
    .trace-pending .trace-badge {{ background: rgba(56, 189, 248, 0.16); color: #0369a1; }}
    .trace-container:empty::before {{
      content: "等待店铺或产品跳转结果";
      display: grid;
      min-height: 100%;
      place-items: center;
      color: #64748b;
      font-size: 13px;
      font-weight: 600;
    }}
    .iframe-container {{
      width: 100%;
      height: 100%;
      border: none;
      background: white;
      border-radius: 0 0 10px 10px;
    }}
    .report-preview-shell {{
      position: relative;
      height: 100%;
      min-height: 520px;
      background: #ffffff;
    }}
    .report-preview-shell .empty-state {{
      position: absolute;
      inset: 0;
      z-index: 1;
      background: #ffffff;
    }}
    .report-preview-shell.has-report .empty-state {{
      display: none;
    }}
    .reports-list {{
      height: 100%;
      min-height: 520px;
      overflow-y: auto;
      background: #ffffff;
      scrollbar-width: thin;
      scrollbar-color: #cbd5e1 transparent;
    }}
    .reports-list::-webkit-scrollbar {{
      width: 6px;
    }}
    .reports-list::-webkit-scrollbar-track {{
      background: transparent;
    }}
    .reports-list::-webkit-scrollbar-thumb {{
      background: #cbd5e1;
      border-radius: 3px;
    }}
    .reports-list::-webkit-scrollbar-thumb:hover {{
      background: #94a3b8;
    }}
    .report-item {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 14px;
      border-bottom: 1px solid #e2e8f0;
      cursor: pointer;
      transition: all 0.2s ease;
      gap: 10px;
    }}
    .report-item:last-child {{ border-bottom: none; }}
    .report-item:hover {{ background: #f8fafc; }}
    .empty-state {{
      min-height: 220px;
      display: grid;
      place-items: center;
      padding: 24px;
      color: #94a3b8;
      font-size: 13px;
      font-weight: 600;
      text-align: center;
    }}
    .report-info {{
      flex: 1;
      min-width: 0;
    }}
    .report-name {{
      font-weight: 600;
      font-size: 13px;
      color: #0f172a;
      overflow: hidden;
      text-overflow: ellipsis;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      word-break: break-word;
    }}
    .report-meta {{
      font-size: 11px;
      color: #94a3b8;
      margin-top: 2px;
    }}
    .hint-text {{
      font-size: 11px;
      color: #94a3b8;
      line-height: 1.5;
    }}
    .message-box {{
      padding: 10px 12px;
      border-radius: 6px;
      margin-top: 10px;
      font-size: 12px;
      background: #f1f5f9;
      color: #0f172a;
      border: 1px solid #e2e8f0;
      transition: all 0.2s ease;
    }}
    .message-box.success {{
      background: rgba(34, 197, 94, 0.1);
      color: #16a34a;
      border-color: rgba(34, 197, 94, 0.2);
    }}
    .message-box.error {{
      background: rgba(239, 68, 68, 0.1);
      color: #dc2626;
      border-color: rgba(239, 68, 68, 0.2);
    }}
    .message-box.info {{
      background: rgba(6, 182, 212, 0.1);
      color: #0891b2;
      border-color: rgba(6, 182, 212, 0.2);
    }}
    .text-center {{ text-align: center; }}
    .hidden {{ display: none; }}
    .mt-8 {{ margin-top: 8px; }}
    .mt-10 {{ margin-top: 10px; }}
    .mt-12 {{ margin-top: 12px; }}
    .form-group-row {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }}
    .checkbox-list-2col {{
      grid-template-columns: repeat(2, 1fr) !important;
      gap: 6px !important;
    }}
    .device-pill-status {{
      font-size: 11px;
      color: #94a3b8;
    }}
    .run-device-details {{
      grid-column: 2 / 4;
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
      margin-top: 1px;
      color: #94a3b8;
      font-size: 10px;
    }}
    .run-device-details span {{
      padding: 2px 6px;
      background: #f1f5f9;
      border-radius: 3px;
      max-width: 100%;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      border: 1px solid #e2e8f0;
    }}
    @media (max-width: 1240px) {{
      body {{ overflow: auto; }}
      .main-container {{
        height: auto;
        min-height: calc(100vh - var(--header-height));
        grid-template-columns: 1fr;
        overflow: visible;
      }}
      .sidebar {{
        position: static;
        height: auto;
        max-height: none;
        overflow: visible;
        padding-right: 0;
      }}
      main {{
        min-height: 720px;
      }}
    }}
    @media (max-width: 768px) {{
      :root {{ --header-height: 112px; --page-gap: 12px; }}
      header {{ padding: 12px 16px; }}
      html,
      body {{
        max-width: 100%;
        overflow-x: hidden;
      }}
      .header-content {{ flex-direction: column; align-items: stretch; gap: 10px; }}
      .brand {{ gap: 10px; }}
      .brand-icon {{ width: 36px; height: 36px; font-size: 16px; }}
      .brand-text h1 {{ font-size: 14px; }}
      .brand-text small {{ font-size: 10px; }}
      .status-indicator {{ margin-left: 0; justify-content: flex-start; }}
      .main-container {{
        width: 100vw;
        max-width: 100vw;
        padding: 12px 24px 12px 12px;
        gap: 12px;
      }}
      .panel-body {{ padding: 12px; }}
      .panel-header {{
        padding: 12px;
        flex-wrap: wrap;
        align-items: flex-start;
      }}
      .panel-header .btn-group {{
        display: grid;
        grid-template-columns: 1fr;
        width: 100%;
        max-width: 100%;
      }}
      .panel-header .btn-group .btn {{
        width: 100%;
        flex: none;
        padding-left: 10px;
        padding-right: 10px;
        white-space: normal;
        overflow-wrap: anywhere;
      }}
      .device-summary {{ grid-template-columns: 1fr; }}
      .device-card {{ grid-template-columns: auto minmax(0, 1fr); }}
      .device-card .device-status {{ grid-column: 2; justify-self: start; }}
      .metrics-grid {{ grid-template-columns: repeat(2, 1fr); }}
      .trace-summary {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .trace-list {{ grid-template-columns: 1fr; }}
      .tabs-header {{ overflow-x: auto; }}
      .tab-btn {{ min-width: 100px; white-space: nowrap; }}
      .btn-group .btn {{ min-width: 0; }}
      .form-group-row {{ grid-template-columns: 1fr; }}
      .number-grid,
      .range-group,
      .option-grid,
      .preset-grid {{
        grid-template-columns: 1fr;
      }}
      .selection-combo {{
        grid-template-columns: minmax(0, 1fr);
      }}
      .selection-action {{
        width: 100%;
        min-height: 34px;
        border-left: 0;
        border-top: 1px solid #e2e8f0;
      }}
      .log-container,
      .report-preview-shell,
      .reports-list {{
        min-height: 520px;
      }}
      .log-line {{
        grid-template-columns: 62px 54px minmax(0, 1fr);
      }}
      .log-device {{
        display: none;
      }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="header-content">
      <div class="brand">
        <div class="brand-icon">PC</div>
        <div class="brand-text">
          <h1>产品中心自动化控制台</h1>
          <small>Appium 多设备运行与报告预览</small>
        </div>
      </div>
      <div class="status-indicator">
        <div id="runStatus" class="status-badge idle">
          <span class="dot"></span>
          <span>空闲</span>
        </div>
      </div>
    </div>
  </header>

  <div class="main-container">
    <aside class="sidebar">
      <div class="panel">
        <div class="panel-header">
          <h2>运行设置</h2>
        </div>
        <div class="panel-body">
          <div class="form-group">
            <label class="form-label" for="mode">运行模式</label>
            <select id="mode" class="form-control">
              <option value="smoke">Smoke (快速)</option>
              <option value="full">Full (完整)</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label" for="appiumServerUrl">Appium 服务地址</label>
            <input id="appiumServerUrl" class="form-control" value="http://127.0.0.1:4725/wd/hub" placeholder="http://localhost:4725/wd/hub">
          </div>
          <div class="form-group">
            <label class="form-label" for="deviceName">默认设备名</label>
            <input id="deviceName" class="form-control" value="Android" placeholder="Android">
          </div>
        </div>
      </div>

      <div class="panel">
        <div class="panel-header">
          <h2>设备选择</h2>
          <div class="btn-group">
            <button class="btn btn-sm btn-secondary" onclick="refreshDevices()">刷新</button>
            <button class="btn btn-sm btn-secondary" onclick="selectOnlineDevices()">全选在线</button>
            <button class="btn btn-sm btn-secondary" onclick="clearDeviceSelection()">清空</button>
          </div>
        </div>
        <div class="panel-body">
          <div class="device-summary">
            <div class="device-summary-item">
              <strong id="onlineDeviceCount">0</strong>
              <span>在线</span>
            </div>
            <div class="device-summary-item">
              <strong id="selectedDeviceCount">0</strong>
              <span>已选</span>
            </div>
            <div class="device-summary-item">
              <strong id="totalDeviceCount">0</strong>
              <span>发现</span>
            </div>
          </div>
          <div id="deviceList" class="device-grid">
            <p class="hint-text text-center">点击刷新按钮检测设备</p>
          </div>
          <p class="hint-text mt-12">未选择已发现设备时，将使用默认设备名运行单设备任务</p>
        </div>
      </div>

      <div class="panel">
        <div class="panel-header">
          <h2>执行用例</h2>
          <div class="btn-group">
            <button class="btn btn-sm btn-secondary" onclick="selectAllTests()">全选</button>
            <button class="btn btn-sm btn-secondary" onclick="clearTests()">清空</button>
          </div>
        </div>
        <div class="panel-body">
          <div id="testsList" class="checkbox-list"></div>
        </div>
      </div>

      <div class="panel">
        <div class="panel-header">
          <h2>筛选范围</h2>
        </div>
        <div class="panel-body">
          <div class="config-section">
            <div class="section-title">筛选范围</div>
            <div class="form-group">
              <label class="form-label" for="countries">国家/地区</label>
              <div class="selection-combo">
                <div class="selection-main">
                  <div id="countriesSummary" class="selection-chips"></div>
                  <input id="countries" class="selection-input" placeholder="可手动输入，逗号分隔" oninput="updateSelectionSummary('countries', '请选择国家/地区')">
                </div>
                <button class="selection-action" type="button" onclick="togglePicker('countryPicker')">选择</button>
              </div>
              <div id="countryPicker" class="picker-content selector-dropdown">
                <div id="countryOptions" class="checkbox-list"></div>
                <div class="btn-group mt-10">
                  <button class="btn btn-sm btn-secondary" onclick="selectAllCountries()">全选</button>
                  <button class="btn btn-sm btn-secondary" onclick="clearCountries()">清空</button>
                </div>
              </div>
            </div>
            <div class="form-group">
              <label class="form-label" for="channels">渠道</label>
              <div class="selection-combo">
                <div class="selection-main">
                  <div id="channelsSummary" class="selection-chips"></div>
                  <input id="channels" class="selection-input" placeholder="可手动输入，逗号分隔" oninput="updateSelectionSummary('channels', '请选择渠道')">
                </div>
                <button class="selection-action" type="button" onclick="togglePicker('channelPicker')">选择</button>
              </div>
              <div id="channelPicker" class="picker-content selector-dropdown">
                <div id="channelOptions" class="checkbox-list"></div>
                <div class="btn-group mt-10">
                  <button class="btn btn-sm btn-secondary" onclick="selectAllChannels()">全选</button>
                  <button class="btn btn-sm btn-secondary" onclick="clearChannels()">清空</button>
                </div>
              </div>
            </div>
            <div class="form-group">
              <label class="form-label" for="products">产品</label>
              <div class="selection-combo">
                <div class="selection-main">
                  <div id="productsSummary" class="selection-chips"></div>
                  <input id="products" class="selection-input" placeholder="可手动输入，逗号分隔" oninput="updateSelectionSummary('products', '请选择产品')">
                </div>
                <button class="selection-action" type="button" onclick="togglePicker('productPicker')">选择</button>
              </div>
              <div id="productPicker" class="picker-content selector-dropdown">
                <div id="productOptions" class="checkbox-list"></div>
                <div class="btn-group mt-10">
                  <button class="btn btn-sm btn-secondary" onclick="selectAllProducts()">全选</button>
                  <button class="btn btn-sm btn-secondary" onclick="clearProducts()">清空</button>
                </div>
              </div>
            </div>
          </div>

          <div class="config-section">
            <div class="section-title">执行参数</div>
            <div class="number-grid form-group">
              <div class="number-card">
              <label class="form-label" for="channelMax">渠道最大用例数</label>
              <input id="channelMax" class="form-control" type="number" min="0" value="0">
              </div>
              <div class="number-card">
              <label class="form-label" for="productMax">产品最大用例数</label>
              <input id="productMax" class="form-control" type="number" min="0" value="0">
              </div>
            </div>
            <div class="range-group">
              <div class="range-field">
                <label class="form-label" for="startAt">断点开始</label>
                <input id="startAt" class="form-control" placeholder="国家|渠道|产品">
              </div>
              <div class="range-field">
                <label class="form-label" for="endAt">断点结束</label>
                <input id="endAt" class="form-control" placeholder="国家|渠道|产品">
              </div>
              <div class="range-actions">
                <button class="btn btn-sm btn-secondary" type="button" onclick="fillLatestFailureBreakpoint()">填失败断点</button>
                <button class="btn btn-sm btn-secondary" type="button" onclick="clearBreakpointFields()">清空断点</button>
              </div>
            </div>
          </div>

          <div class="config-section">
            <div class="section-title">校验选项</div>
            <div class="option-grid">
            <label class="checkbox-item option-card">
              <input id="relaxedBrowser" type="checkbox">
              <span class="checkbox-title">快速浏览器校验</span>
            </label>
            <label class="checkbox-item option-card">
              <input id="strictOfficialUrl" type="checkbox">
              <span class="checkbox-title">严格官网 URL</span>
            </label>
            <label class="checkbox-item option-card">
              <input id="strictProductDestination" type="checkbox" checked>
              <span class="checkbox-title">严格商品目标</span>
            </label>
            <label class="checkbox-item option-card">
              <input id="productTextFallback" type="checkbox">
              <span class="checkbox-title">商品文字兜底</span>
            </label>
            <label class="checkbox-item option-card">
              <input id="hardReset" type="checkbox">
              <span class="checkbox-title">跳转后硬重置</span>
            </label>
            </div>
          </div>
        </div>
      </div>

      <div class="panel">
        <div class="panel-header">
          <h2>快捷填充</h2>
        </div>
        <div class="panel-body">
          <div class="config-section">
            <div class="section-title">快捷填充</div>
            <div class="preset-grid">
              <button class="btn btn-secondary preset-btn" onclick="fillSmoke()">Smoke 范围</button>
              <button class="btn btn-secondary preset-btn" onclick="fillFull()">全量范围</button>
              <button class="btn btn-secondary preset-btn" onclick="clearFilters()">清空筛选</button>
            </div>
          </div>
        </div>
      </div>

      <div class="panel">
        <div class="panel-header">
          <h2>操作</h2>
        </div>
        <div class="panel-body">
          <div class="btn-group">
            <button id="runBtn" class="btn btn-primary" onclick="startRun()">开始运行</button>
            <button id="stopBtn" class="btn btn-danger" onclick="stopRun()" disabled>停止</button>
          </div>
          <button class="btn btn-secondary mt-8" style="width: 100%;" onclick="refreshReports()">刷新报告</button>
          <div id="messageBox" class="message-box"></div>
        </div>
      </div>
    </aside>

    <main>
      <div class="metrics-grid">
        <div class="metric-card">
          <div class="metric-value" id="startedAt">-</div>
          <div class="metric-label">开始时间</div>
        </div>
        <div class="metric-card">
          <div class="metric-value" id="finishedAt">-</div>
          <div class="metric-label">结束时间</div>
        </div>
        <div class="metric-card">
          <div class="metric-value" id="exitCode">-</div>
          <div class="metric-label">退出码</div>
        </div>
        <div class="metric-card">
          <div class="metric-value" id="deviceCount">-</div>
          <div class="metric-label">运行设备</div>
        </div>
        <div class="metric-card">
          <div class="metric-value" id="latestReport">-</div>
          <div class="metric-label">最新报告</div>
        </div>
      </div>

      <div id="runningDevices" class="metrics-summary"></div>

      <div class="tabs-container">
        <div class="tabs-header">
          <button id="tabLog" class="tab-btn active" onclick="switchTab('log')">运行日志</button>
          <button id="tabTrace" class="tab-btn" onclick="switchTab('trace')">跳转结果</button>
          <button id="tabReport" class="tab-btn" onclick="switchTab('report')">报告预览</button>
          <button id="tabList" class="tab-btn" onclick="switchTab('list')">历史报告</button>
        </div>
        <div class="tab-content">
          <div id="viewLog" class="tab-view">
            <div id="logContent" class="log-container"></div>
          </div>
          <div id="viewTrace" class="tab-view hidden">
            <div id="traceContent" class="trace-container"></div>
          </div>
          <div id="viewReport" class="tab-view hidden">
            <div id="reportPreviewShell" class="report-preview-shell">
              <div id="reportEmpty" class="empty-state">等待报告生成后预览</div>
              <iframe id="reportFrame" class="iframe-container" title="测试报告"></iframe>
            </div>
          </div>
          <div id="viewList" class="tab-view hidden">
            <div id="reportsList" class="reports-list"></div>
          </div>
        </div>
      </div>
    </main>
  </div>

  <script>
    const state = { config: null, devices: [], logOffset: 0, activeTab: "log", deviceNameTouched: false, jumpCards: [] };
    const TEST_META = {
      test_01_enter_product_center: { title: "01 进入产品中心", note: "启动 App，处理弹窗，进入产品中心并校验页面基础元素。" },
      test_02_country_dropdown_options: { title: "02 国家/地区选项", note: "检查国家/地区下拉列表是否包含预期选项。" },
      test_02_country_switch_updates_purchase_channels: { title: "02 国家切换刷新渠道", note: "连续切换中国、美国、日本、其他地区等国家，确认购买渠道随国家变化刷新。" },
      test_02_purchase_channels_display: { title: "02 各国渠道展示", note: "逐个国家检查购买渠道是否展示完整，例如淘宝、JD、Amazon、AliExpress、本地经销商。" },
      test_03_purchase_channels_jump: { title: "03 购买渠道跳转", note: "按国家和渠道验证淘宝、JD、Amazon、AliExpress、本地经销商等跳转。" },
      test_04_featured_products_jump: { title: "04 主打产品跳转", note: "按国家、渠道、产品验证主打产品是否跳到对应购买页或网页。" },
      test_04_featured_products_display: { title: "04 主打产品展示", note: "检查产品中心主打产品列表是否展示配置中的产品。" },
      test_05_other_region_direct_jump: { title: "05 其他地区直跳", note: "验证其他地区的本地经销商官网跳转和官网产品页跳转。" }
    };

    function $(id) { return document.getElementById(id); }
    function escapeHtml(v) { return String(v).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[c])); }
    function escapeAttr(v) { return escapeHtml(v); }

    function splitDeviceLog(text) {
      const match = String(text || "").match(/^\[([^\]]+)\]\s*(.*)$/);
      return match ? { device: match[1], message: match[2] } : { device: "", message: String(text || "") };
    }

    function classifyLogMessage(message) {
      const text = String(message || "");
      if (/失败|异常|错误|未命中|Traceback|AssertionError|Error|ERROR/.test(text)) return { type: "fail", label: "错误" };
      if (/跳过|skip|SKIP/.test(text)) return { type: "warn", label: "跳过" };
      if (/通过|成功|已打开目标|命中|已确认|已回到|已关闭|跳转成功/.test(text)) return { type: "pass", label: "通过" };
      if (/点击|坐标|Flutter|content-desc|bounds=/.test(text)) return { type: "click", label: "点击" };
      if (/开始测试|开始配置|启动命令|工作目录|设备参数|当前为|断点开始|断点结束/.test(text)) return { type: "start", label: "开始" };
      if (/恢复|重试|返回|重建|重置|外部页面|未生效/.test(text)) return { type: "warn", label: "恢复" };
      return { type: "info", label: "信息" };
    }

    function renderLogLine(item) {
      const parsed = splitDeviceLog(item.text);
      const meta = classifyLogMessage(parsed.message);
      return `
        <div class="log-line log-${meta.type}">
          <span class="log-time">${escapeHtml(item.time || "")}</span>
          <span class="log-level">${escapeHtml(meta.label)}</span>
          <span class="log-device" title="${escapeAttr(parsed.device)}">${escapeHtml(parsed.device || "-")}</span>
          <span class="log-message">${escapeHtml(parsed.message)}</span>
        </div>
      `;
    }

    function compactMessage(text) {
      return String(text || "").replace(/\s+/g, " ").trim();
    }

    function splitJumpSubject(subject) {
      const text = compactMessage(subject);
      const countries = state.config?.countries || [];
      const channels = [...new Set([...(state.config?.channels || []), "本地经销商", "Amazon", "AliExpress", "淘宝", "JD"])]
        .sort((a, b) => b.length - a.length);
      let country = "";
      let rest = text;
      const countryHit = countries.find(item => rest === item || rest.startsWith(`${item} `));
      if (countryHit) {
        country = countryHit;
        rest = compactMessage(rest.slice(countryHit.length));
      }
      if (rest.includes(" / ")) {
        const parts = rest.split(" / ").map(compactMessage);
        return { country, channel: parts[0] || "", product: parts.slice(1).join(" / ") || "", raw: text };
      }
      const channelHit = channels.find(item => rest === item || rest.startsWith(`${item} `));
      if (channelHit) {
        return { country, channel: channelHit, product: compactMessage(rest.slice(channelHit.length)), raw: text };
      }
      return { country, channel: "", product: rest, raw: text };
    }

    function jumpKey(parts) {
      return [parts.country || "", parts.channel || "", parts.product || parts.raw || ""].join("|");
    }

    function parseJumpEvent(item) {
      const parsed = splitDeviceLog(item.text);
      const message = compactMessage(parsed.message);
      if (!message) return null;

      if (/当前在外部页面|常规返回无效|尝试返回|切回被测 App|已回到产品中心|恢复|重试|未生效/.test(message)) {
        return null;
      }

      let match = message.match(/^(.+?)\s+链接\/intent 目标校验通过：命中\s+(.+)$/);
      if (match) {
        const parts = splitJumpSubject(match[1]);
        return {
          kind: "check",
          key: jumpKey(parts),
          status: "pending",
          label: "目标已命中",
          country: parts.country,
          channel: parts.channel,
          product: parts.product,
          title: parts.product || parts.channel || parts.raw,
          matched: match[2],
          destination: "",
          time: item.time,
          device: parsed.device,
        };
      }

      match = message.match(/^(.+?)\s+跳转成功：(.+)$/);
      if (match) {
        const parts = splitJumpSubject(match[1]);
        return {
          kind: "result",
          key: jumpKey(parts),
          status: "pass",
          label: "跳转成功",
          country: parts.country,
          channel: parts.channel,
          product: parts.product,
          title: parts.product || parts.channel || parts.raw,
          matched: "",
          destination: match[2],
          time: item.time,
          device: parsed.device,
        };
      }

      match = message.match(/^点击\s+(.+?)\s+后没有跳转到(.+)$/);
      if (match) {
        const parts = splitJumpSubject(match[1]);
        return {
          kind: "result",
          key: jumpKey(parts),
          status: "fail",
          label: "未跳转",
          country: parts.country,
          channel: parts.channel,
          product: parts.product,
          title: parts.product || parts.channel || parts.raw,
          matched: "",
          destination: `没有跳转到${match[2]}`,
          time: item.time,
          device: parsed.device,
        };
      }

      match = message.match(/^(.+?)\s+跳转失败：(.+)$/);
      if (match) {
        const parts = splitJumpSubject(match[1]);
        return {
          kind: "result",
          key: jumpKey(parts),
          status: "fail",
          label: "跳转失败",
          country: parts.country,
          channel: parts.channel,
          product: parts.product,
          title: parts.product || parts.channel || parts.raw,
          matched: "",
          destination: match[2],
          time: item.time,
          device: parsed.device,
        };
      }
      return null;
    }

    function findJumpCard(event) {
      return state.jumpCards.find(card => card.key === event.key && card.status !== "pass")
        || state.jumpCards.slice().reverse().find(card =>
          (
            (event.product && card.product === event.product)
            || (!event.product && event.channel && card.channel === event.channel)
          )
          && card.status !== "pass"
        );
    }

    function applyJumpEvent(event) {
      const existing = findJumpCard(event);
      if (existing) {
        Object.assign(existing, {
          status: event.status === "pending" && existing.status === "pass" ? existing.status : event.status,
          label: event.status === "pending" && existing.label ? existing.label : event.label,
          country: existing.country || event.country,
          channel: existing.channel || event.channel,
          product: existing.product || event.product,
          title: existing.title || event.title,
          matched: existing.matched || event.matched,
          destination: event.destination || existing.destination,
          time: event.time || existing.time,
          device: event.device || existing.device,
        });
        return;
      }
      state.jumpCards.push(event);
    }

    function appendTraceEvents(logs) {
      const events = (logs || []).map(parseJumpEvent).filter(Boolean);
      if (!events.length) return;
      events.forEach(applyJumpEvent);
      if (state.jumpCards.length > 300) state.jumpCards = state.jumpCards.slice(-300);
      renderTrace();
    }

    function renderTrace() {
      const root = $("traceContent");
      if (!root) return;
      if (!state.jumpCards.length) {
        root.innerHTML = "";
        return;
      }
      const totals = state.jumpCards.reduce((acc, item) => {
        acc.total += 1;
        acc[item.status] = (acc[item.status] || 0) + 1;
        return acc;
      }, { total: 0, pass: 0, fail: 0, pending: 0 });
      const summary = `
        <div class="trace-summary">
          <div class="trace-stat"><strong>${totals.total}</strong><span>跳转项</span></div>
          <div class="trace-stat"><strong>${totals.pass}</strong><span>跳转成功</span></div>
          <div class="trace-stat"><strong>${totals.pending}</strong><span>已命中待跳转</span></div>
          <div class="trace-stat"><strong>${totals.fail}</strong><span>失败/异常</span></div>
        </div>
      `;
      const rows = state.jumpCards.slice().reverse().map(item => {
        const title = item.product || item.channel || item.title || "跳转项";
        const chips = [
          item.country ? `国家/地区：${item.country}` : "",
          item.channel ? `渠道/店铺：${item.channel}` : "",
          item.device ? `设备：${item.device}` : "",
        ].filter(Boolean);
        return `
        <div class="trace-card trace-${escapeAttr(item.status)}">
          <div class="trace-card-head">
            <div>
              <div class="trace-title">${escapeHtml(title)}</div>
              <div class="trace-subtitle">${chips.map(chip => `<span class="trace-chip">${escapeHtml(chip)}</span>`).join("")}</div>
            </div>
            <span class="trace-badge">${escapeHtml(item.label)}</span>
          </div>
          <div class="trace-result">
            <div class="trace-result-label">跳转结果</div>
            <div class="trace-detail">${escapeHtml(item.destination || "目标链接/intent 已命中，等待跳转结果")}</div>
            ${item.matched ? `<div class="trace-detail">命中：${escapeHtml(item.matched)}</div>` : ""}
          </div>
          <div class="trace-meta">
            <span class="trace-time">${escapeHtml(item.time || "")}</span>
          </div>
        </div>
      `}).join("");
      root.innerHTML = summary + `<div class="trace-list">${rows}</div>`;
    }

    function selectedChecks(name) {
      return Array.from(document.querySelectorAll(`input[name="${name}"]:checked`)).map(el => el.value);
    }

    function commaValue(id) {
      return $(id).value.split(",").map(v => v.trim()).filter(Boolean);
    }

    function selectedOrTyped(name, id) {
      const selected = selectedChecks(name);
      return selected.length ? selected : commaValue(id);
    }

    function syncInputFromChecks(name) {
      const input = $(name);
      if (!input) return;
      input.value = selectedChecks(name).join(",");
      updateSelectionSummary(name);
    }

    function updateSelectionSummary(id, emptyText = "") {
      const root = $(`${id}Summary`);
      if (!root) return;
      const labels = {
        countries: "请选择国家/地区",
        channels: "请选择渠道",
        products: "请选择产品",
      };
      const values = commaValue(id);
      if (!values.length) {
        root.innerHTML = `<span class="selection-empty">${escapeHtml(emptyText || labels[id] || "请选择")}</span>`;
        return;
      }
      const visible = values.slice(0, 2);
      const more = values.length - visible.length;
      root.innerHTML = visible.map(item => `<span class="selection-chip" title="${escapeAttr(item)}">${escapeHtml(item)}</span>`).join("") +
        (more > 0 ? `<span class="selection-chip more">+${more}</span>` : "");
    }

    function updateAllSelectionSummaries() {
      updateSelectionSummary("countries", "请选择国家/地区");
      updateSelectionSummary("channels", "请选择渠道");
      updateSelectionSummary("products", "请选择产品");
    }

    async function apiCall(method, path, data = null) {
      const options = { method };
      if (data) {
        options.headers = { "Content-Type": "application/json" };
        options.body = JSON.stringify(data);
      }
      const res = await fetch(path, options);
      return res.json();
    }

    function renderDeviceCard(device, selectedSet = null) {
      const isOnline = device.state === "device";
      const isSelected = selectedSet ? selectedSet.has(device.udid) : selectedChecks("devices").includes(device.udid);
      const meta = [device.product, device.model && device.model !== device.name ? device.model : "", device.transportId ? "transport " + device.transportId : ""].filter(Boolean);
      return `
        <label class="device-card ${isSelected ? 'selected' : ''} ${!isOnline ? 'disabled' : ''}">
          <input type="checkbox" name="devices" value="${escapeAttr(device.udid)}" ${!isOnline ? 'disabled' : ''} ${isSelected ? 'checked' : ''} class="device-radio">
          <div class="device-info">
            <div class="device-name">${escapeHtml(device.name || device.udid)}</div>
            <div class="device-udid">${escapeHtml(device.udid)}</div>
            ${meta.length ? `<div class="device-meta">${meta.map(item => `<span>${escapeHtml(item)}</span>`).join("")}</div>` : ""}
          </div>
          <span class="device-status ${isOnline ? 'online' : 'offline'}">${isOnline ? '在线' : device.state}</span>
        </label>
      `;
    }

    document.addEventListener("change", event => {
      if (event.target.matches('input[name="devices"]')) {
        event.target.closest(".device-card")?.classList.toggle("selected", event.target.checked);
        updateDeviceSummary();
        autoFillDeviceName();
      }
    });

    document.addEventListener("input", event => {
      if (event.target.id === "deviceName") {
        state.deviceNameTouched = true;
      }
    });

    function deviceDisplayName(device) {
      if (!device) return "";
      return device.name || device.model || device.product || device.udid || "";
    }

    function autoFillDeviceName(force = false) {
      const input = $("deviceName");
      if (!input || (!force && state.deviceNameTouched)) return;
      const selectedDevice = selectedDevices()[0];
      const onlineDevice = state.devices.find(device => device.state === "device");
      const fallbackDevice = state.devices[0];
      const name = deviceDisplayName(selectedDevice || onlineDevice || fallbackDevice);
      if (name && (force || !state.deviceNameTouched)) {
        input.value = name;
      }
    }

    function renderDevices(items, autoSelectOnline = false) {
      const previousSelection = new Set(selectedChecks("devices"));
      state.devices = items || [];
      const root = $("deviceList");
      if (!state.devices.length) {
        root.innerHTML = '<p class="hint-text text-center">未发现已连接设备</p>';
        updateDeviceSummary();
        return;
      }
      const currentIds = new Set(state.devices.map(d => d.udid));
      let selected = new Set(Array.from(previousSelection).filter(udid => currentIds.has(udid)));
      if (autoSelectOnline && !selected.size) {
        selected = new Set(state.devices.filter(d => d.state === "device").map(d => d.udid));
      }
      root.innerHTML = state.devices.map(device => renderDeviceCard(device, selected)).join("");
      updateDeviceSummary();
      autoFillDeviceName();
    }

    function updateDeviceSummary() {
      const online = state.devices.filter(d => d.state === "device").length;
      const selected = selectedChecks("devices").length;
      $("onlineDeviceCount").textContent = online;
      $("selectedDeviceCount").textContent = selected;
      $("totalDeviceCount").textContent = state.devices.length;
    }

    async function refreshDevices() {
      const data = await apiCall("GET", "/api/devices");
      renderDevices(data.devices || [], true);
      autoFillDeviceName();
      showMessage("已刷新设备：" + (data.devices || []).length + " 台", "info");
    }

    function selectOnlineDevices() {
      const online = state.devices.filter(d => d.state === "device").map(d => d.udid);
      setChecks("devices", online);
      updateDeviceSummary();
      autoFillDeviceName();
    }

    function clearDeviceSelection() {
      setChecks("devices", []);
      updateDeviceSummary();
    }

    function setChecks(name, values) {
      const wanted = new Set(values);
      document.querySelectorAll(`input[name="${name}"]`).forEach(input => {
        input.checked = wanted.has(input.value);
        if (name === "devices") {
          input.closest(".device-card")?.classList.toggle("selected", input.checked);
        }
      });
      if (["countries", "channels", "products"].includes(name)) {
        syncInputFromChecks(name);
      }
      if (name === "devices") updateDeviceSummary();
    }

    function renderTests(items) {
      const root = $("testsList");
      root.innerHTML = items.map(item => {
        const meta = TEST_META[item];
        return `
          <label class="checkbox-item">
            <input type="checkbox" name="tests" value="${escapeAttr(item)}" ${item === "test_04_featured_products_jump" ? 'checked' : ''}>
            <div class="checkbox-content">
              <div class="checkbox-title">${meta ? escapeHtml(meta.title) : escapeHtml(item)}</div>
              ${meta ? `<div class="checkbox-desc">${escapeHtml(meta.note)}</div>` : ''}
              <div class="checkbox-code">${escapeHtml(item)}</div>
            </div>
          </label>
        `;
      }).join("");
    }

    function toggleCheckboxGroup(name, state) {
      document.querySelectorAll(`input[name="${name}"]`).forEach(input => input.checked = state);
      // 如果是设备，也要更新样式
      if (name === "devices") {
        document.querySelectorAll(`input[name="devices"]`).forEach(input => {
          input.closest(".device-card")?.classList.toggle("selected", input.checked);
        });
      }
    }

    function selectAllTests() {
      toggleCheckboxGroup("tests", true);
    }

    function clearTests() {
      toggleCheckboxGroup("tests", false);
    }

    function renderOptions(id, name, items) {
      const root = $(id);
      root.innerHTML = items.map(item => `
        <label class="checkbox-item">
          <input type="checkbox" name="${name}" value="${escapeAttr(item)}" onchange="syncInputFromChecks('${escapeAttr(name)}')">
          <span class="checkbox-title">${escapeHtml(item)}</span>
        </label>
      `).join("");
    }

    function togglePicker(id) {
      const picker = $(id);
      picker.classList.toggle("expanded");
      picker.previousElementSibling?.classList.toggle("expanded");
    }

    function selectAllGroup(configKey, checkboxName) {
      setChecks(checkboxName, state.config?.[configKey] || []);
    }

    function clearGroup(checkboxName, inputId) {
      setChecks(checkboxName, []);
      if (inputId) $(inputId).value = "";
    }

    function selectAllCountries() {
      selectAllGroup("countries", "countries");
    }

    function clearCountries() {
      clearGroup("countries", "countries");
    }

    function selectAllChannels() {
      selectAllGroup("channels", "channels");
    }

    function clearChannels() {
      clearGroup("channels", "channels");
    }

    function selectAllProducts() {
      selectAllGroup("products", "products");
    }

    function clearProducts() {
      clearGroup("products", "products");
    }

    async function loadConfig() {
      state.config = await apiCall("GET", "/api/config");
      $("appiumServerUrl").value = state.config.defaults.appiumServerUrl;
      $("deviceName").value = state.config.defaults.deviceName;
      $("mode").value = state.config.defaults.mode || "full";
      renderDevices(state.config.devices || [], true);
      autoFillDeviceName();
      renderTests(state.config.tests || []);
      renderOptions("countryOptions", "countries", state.config.countries || []);
      renderOptions("channelOptions", "channels", state.config.channels || []);
      renderOptions("productOptions", "products", state.config.products || []);
      updateAllSelectionSummaries();
      renderReports(state.config.reports || []);
      if ((state.config.reports || []).length) {
        showReport(reportPreviewUrl(state.config.reports[0]), state.config.reports[0].name);
      }
    }

    function fillSmoke() {
      $("mode").value = "smoke";
      const smokeCountries = (state.config?.countries || []).filter((_, i) => [0, 1, 4].includes(i));
      setChecks("countries", smokeCountries);
      setChecks("channels", []);
      setChecks("products", ["CoMo SE", "CoMo"]);
      $("channelMax").value = "4";
      $("productMax").value = "8";
    }

    function fillFull() {
      $("mode").value = "full";
      setChecks("countries", []);
      setChecks("channels", []);
      setChecks("products", []);
      $("channelMax").value = "0";
      $("productMax").value = "0";
    }

    function clearFilters() {
      ["countries", "channels", "products", "startAt", "endAt"].forEach(id => $(id).value = "");
      setChecks("countries", []);
      setChecks("channels", []);
      setChecks("products", []);
      updateAllSelectionSummaries();
      $("channelMax").value = "0";
      $("productMax").value = "0";
    }

    function selectedDevices() {
      const selected = selectedChecks("devices");
      return selected.map(udid => state.devices.find(d => d.udid === udid)).filter(Boolean).map(d => ({ name: d.name || d.model || d.udid, udid: d.udid }));
    }

    function payload() {
      return {
        mode: $("mode").value,
        appiumServerUrl: $("appiumServerUrl").value,
        deviceName: $("deviceName").value,
        devices: selectedDevices(),
        tests: selectedChecks("tests"),
        countries: selectedOrTyped("countries", "countries"),
        channels: selectedOrTyped("channels", "channels"),
        products: selectedOrTyped("products", "products"),
        channelMax: Number($("channelMax").value || 0),
        productMax: Number($("productMax").value || 0),
        startAt: $("startAt").value,
        endAt: $("endAt").value,
        relaxedBrowser: $("relaxedBrowser").checked,
        strictOfficialUrl: $("strictOfficialUrl").checked,
        strictProductDestination: $("strictProductDestination").checked,
        productTextFallback: $("productTextFallback").checked,
        hardReset: $("hardReset").checked,
      };
    }

    function showMessage(msg, type = "info") {
      const box = $("messageBox");
      box.textContent = msg;
      box.className = `message-box ${type}`;
      setTimeout(() => box.className = "message-box", 3000);
    }

    async function startRun() {
      const runPayload = payload();
      if (!runPayload.tests.length) {
        showMessage("请至少选择一个用例", "error");
        return;
      }
      state.logOffset = 0;
      state.jumpCards = [];
      $("logContent").textContent = "";
      $("traceContent").textContent = "";
      clearReportPreview("等待本次任务生成报告");
      const data = await apiCall("POST", "/api/run", runPayload);
      showMessage(data.message, data.ok ? "success" : "error");
      await pollStatus();
    }

    async function stopRun() {
      const data = await apiCall("POST", "/api/stop");
      showMessage(data.message, data.ok ? "info" : "error");
      await pollStatus();
    }

    async function fillLatestFailureBreakpoint() {
      const data = await apiCall("GET", "/api/failure-breakpoint");
      if (!data.ok) {
        showMessage(data.message || "没有可填写的失败断点", "error");
        return;
      }
      $("startAt").value = data.breakpoint;
      $("endAt").value = "";
      showMessage(`已填入断点开始：${data.breakpoint}`, "success");
    }

    function clearBreakpointFields() {
      $("startAt").value = "";
      $("endAt").value = "";
      showMessage("断点已清空", "info");
    }

    function formatDuration(seconds) {
      const value = Number(seconds || 0);
      const minutes = Math.floor(value / 60);
      const rest = value % 60;
      return minutes ? `${minutes}m ${rest}s` : `${rest}s`;
    }

    function renderRunningDevices(devices) {
      const root = $("runningDevices");
      root.innerHTML = "";
      if (!devices || !devices.length) {
        root.style.display = "none";
        return;
      }
      root.style.display = "flex";
      devices.forEach(device => {
        const status = device.running ? "running" : device.exitCode === 0 ? "success" : device.exitCode ? "fail" : "idle";
        const statusText = device.running ? "运行中" : device.exitCode === 0 ? "通过" : device.exitCode ? "失败" : "等待";
        const ports = device.ports || {};
        const details = [
          device.udid ? `UDID ${device.udid}` : "",
          ports.system ? `system ${ports.system}` : "",
          ports.chromedriver ? `chrome ${ports.chromedriver}` : "",
          device.startedAt ? `已用 ${formatDuration(device.durationSeconds)}` : "",
        ].filter(Boolean);
        root.innerHTML += `
          <div class="device-pill ${status}">
            <span class="status-dot"></span>
            <span class="device-name">${escapeHtml(device.name || device.udid)}</span>
            <span class="device-pill-status">${statusText}</span>
            ${details.length ? `<div class="run-device-details">${details.map(item => `<span>${escapeHtml(item)}</span>`).join("")}</div>` : ""}
          </div>
        `;
      });
    }

    async function pollStatus() {
      const data = await apiCall("GET", "/api/status");
      $("startedAt").textContent = data.startedAt || "-";
      $("finishedAt").textContent = data.finishedAt || "-";
      $("exitCode").textContent = data.exitCode === null ? "-" : data.exitCode;
      $("deviceCount").textContent = data.devices?.length || "-";
      $("latestReport").textContent = data.latestReport || "-";
      renderRunningDevices(data.devices || []);
      $("runBtn").disabled = data.running;
      $("stopBtn").disabled = !data.running;
      const status = $("runStatus");
      const statusClass = data.running ? "running" : data.exitCode === 0 ? "success" : data.exitCode ? "fail" : "idle";
      const statusText = data.running ? "运行中" : data.exitCode === 0 ? "已通过" : data.exitCode ? "失败" : "空闲";
      status.className = `status-badge ${statusClass}`;
      status.innerHTML = `<span class="dot"></span><span>${statusText}</span>`;
      await pollLogs();
      if (!data.running) await refreshReports(false);
    }

    async function pollLogs() {
      const data = await apiCall("GET", `/api/logs?offset=${state.logOffset}`);
      if (data.logs.length) {
        const log = $("logContent");
        const atBottom = log.scrollTop + log.clientHeight >= log.scrollHeight - 20;
        log.insertAdjacentHTML("beforeend", data.logs.map(renderLogLine).join(""));
        if (atBottom) log.scrollTop = log.scrollHeight;
        appendTraceEvents(data.logs);
      }
      state.logOffset = data.nextOffset;
    }

    async function refreshReports(shouldNotify = true) {
      const data = await apiCall("GET", "/api/reports");
      renderReports(data.reports || []);
      const latestItem = (data.reports || []).find(item => item.name === data.latest) || (data.reports || [])[0];
      if (latestItem) showReport(reportPreviewUrl(latestItem), latestItem.name);
      if (shouldNotify) showMessage("报告列表已刷新", "info");
    }

    function reportPreviewUrl(item) {
      if (!item) return "";
      return item.version ? `${item.url}?v=${encodeURIComponent(item.version)}` : item.url;
    }

    function clearReportPreview(message = "等待报告生成后预览") {
      const frame = $("reportFrame");
      frame.removeAttribute("src");
      frame.dataset.currentUrl = "";
      $("reportEmpty").textContent = message;
      $("reportPreviewShell")?.classList.remove("has-report");
      $("latestReport").textContent = "-";
    }

    function renderReports(items) {
      const root = $("reportsList");
      if (!items.length) {
        root.innerHTML = '<div class="empty-state">还没有生成报告</div>';
        return;
      }
      root.innerHTML = items.map(item => `
        <div class="report-item">
          <div class="report-info">
            <div class="report-name">${escapeHtml(item.name)}</div>
            <div class="report-meta">${escapeHtml(item.mtime)} · ${Math.ceil(item.size / 1024)} KB</div>
          </div>
          <button class="btn btn-sm btn-secondary" onclick="showReport('${escapeAttr(reportPreviewUrl(item))}', '${escapeAttr(item.name)}'); switchTab('report')">预览</button>
        </div>
      `).join("");
    }

    function showReport(url, name) {
      const frame = $("reportFrame");
      if (frame.dataset.currentUrl !== url) {
        frame.src = url;
        frame.dataset.currentUrl = url;
      }
      $("reportPreviewShell")?.classList.toggle("has-report", Boolean(url));
      $("latestReport").textContent = name || "-";
    }

    function switchTab(name) {
      state.activeTab = name;
      ["log", "trace", "report", "list"].forEach(tab => {
        $(`tab${tab[0].toUpperCase()}${tab.slice(1)}`).classList.toggle("active", tab === name);
        $(`view${tab[0].toUpperCase()}${tab.slice(1)}`).classList.toggle("hidden", tab !== name);
      });
    }

    loadConfig().then(() => {
      pollStatus();
      setInterval(pollStatus, 1500);
    });
  </script>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description="产品中心自动化可视化控制台")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--open", action="store_true", help="open the dashboard in the default browser")
    args = parser.parse_args()

    port = find_available_port(args.host, args.port)
    server = ThreadingHTTPServer((args.host, port), DashboardHandler)
    url = f"http://{args.host}:{port}"
    print(f"产品中心自动化控制台已启动：{url}")
    if args.open:
        webbrowser.open(url, new=2)
    print("按 Ctrl+C 退出")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


# 格式化 INDEX_HTML 并注入 CSS 变量
def format_index_html():
    css_vars = generate_css_variables()
    return INDEX_HTML.replace("{css_variables}", css_vars).replace("{{", "{").replace("}}", "}")


if __name__ == "__main__":
    main()
