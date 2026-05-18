# -*- coding: utf-8 -*-
"""
统一的 CSS 设计系统和样式工具
"""

# 颜色系统
COLORS = {
    # 中性色 - 背景和文字
    "neutral": {
        "bg_primary": "#0f172a",      # 深色背景
        "bg_secondary": "#1e293b",    # 次级背景
        "bg_surface": "#ffffff",      # 卡片背景
        "bg_surface_dark": "#1e293b", # 深色卡片背景
        "bg_light": "#f4f6f8",        # 轻背景
        "bg_lighter": "#f8fafc",      # 更轻背景
        "bg_hover": "#f1f5f9",        # Hover背景
    },
    # 文字色
    "text": {
        "primary": "#0f172a",         # 主文字
        "secondary": "#64748b",       # 次级文字
        "muted": "#94a3b8",           # 弱化文字
        "light": "#f1f5f9",           # 浅色文字
        "white": "#ffffff",           # 白色文字
    },
    # 边框色
    "border": {
        "light": "#e2e8f0",           # 浅边框
        "dark": "#475569",            # 深边框
    },
    # 语义色 - 状态和交互
    "semantic": {
        "primary": "#3b82f6",         # 主色
        "primary_hover": "#2563eb",   # 主色 Hover
        "success": "#22c55e",         # 成功
        "warning": "#f59e0b",         # 警告
        "danger": "#ef4444",          # 危险
        "info": "#06b6d4",            # 信息
        "blue": "#1d4ed8",            # 蓝色
    },
    # 状态色 - 测试报告
    "status": {
        "pass": "#138a4d",            # 通过
        "fail": "#c62828",            # 失败
        "error": "#9f1239",           # 错误
        "skip": "#8a5a00",            # 跳过
    },
    # 浅色背景（用于badge等）
    "light_bg": {
        "success": "#dcfce7",         # 成功浅色
        "warning": "#fef3c7",         # 警告浅色
        "danger": "#fee2e2",          # 危险浅色
        "info": "#cffafe",            # 信息浅色
    }
}

# 间距系统
SPACING = {
    "xs": "4px",
    "sm": "8px",
    "md": "12px",
    "lg": "16px",
    "xl": "24px",
    "2xl": "32px",
}

# 圆角系统
RADIUS = {
    "sm": "4px",
    "md": "6px",
    "lg": "8px",
}

# 阴影系统
SHADOW = {
    "sm": "0 1px 2px 0 rgb(0 0 0 / 0.05)",
    "md": "0 3px 8px rgb(15 23 42 / 0.08)",
    "lg": "0 8px 18px rgb(15 23 42 / 0.12)",
}

# 排版系统
FONT = {
    "family_ui": '"Inter", "Segoe UI", "Microsoft YaHei", system-ui, sans-serif',
    "family_mono": '"JetBrains Mono", "Consolas", monospace',
    "size_sm": "12px",
    "size_base": "14px",
    "size_lg": "16px",
    "size_xl": "18px",
    "size_2xl": "22px",
    "size_3xl": "28px",
    "weight_normal": "400",
    "weight_medium": "500",
    "weight_semibold": "600",
    "weight_bold": "700",
}

# 响应式断点
BREAKPOINTS = {
    "mobile": "500px",
    "tablet": "720px",
    "desktop": "900px",
    "wide": "1200px",
}


def generate_css_variables() -> str:
    """生成 CSS 变量定义"""
    lines = [":root {"]

    # 中性色
    for name, value in COLORS["neutral"].items():
        lines.append(f"  --{name}: {value};")

    # 文字色
    for name, value in COLORS["text"].items():
        lines.append(f"  --text-{name}: {value};")

    # 边框色
    for name, value in COLORS["border"].items():
        lines.append(f"  --border-{name}: {value};")

    # 语义色
    for name, value in COLORS["semantic"].items():
        lines.append(f"  --{name}: {value};")

    # 状态色
    for name, value in COLORS["status"].items():
        lines.append(f"  --status-{name}: {value};")

    # 浅色背景
    for name, value in COLORS["light_bg"].items():
        lines.append(f"  --{name}-light: {value};")

    # 间距
    for name, value in SPACING.items():
        lines.append(f"  --space-{name}: {value};")

    # 圆角
    for name, value in RADIUS.items():
        lines.append(f"  --radius-{name}: {value};")

    # 阴影
    for name, value in SHADOW.items():
        lines.append(f"  --shadow-{name}: {value};")

    lines.append("}")
    return "\n    ".join(lines)


def get_color(category: str, name: str) -> str:
    """获取颜色值"""
    if category == "neutral":
        return COLORS["neutral"].get(name, "")
    elif category == "text":
        return COLORS["text"].get(name, "")
    elif category == "status":
        return COLORS["status"].get(name, "")
    return COLORS[category].get(name, "")


# 预定义的CSS类组合
CSS_HELPERS = {
    "reset": """* { box-sizing: border-box; margin: 0; padding: 0; }""",
    "scroll_smooth": """html { scroll-behavior: smooth; }""",
    "focus_visible": """.tab-btn:focus-visible,
    .btn:focus-visible,
    .form-control:focus-visible {
      outline: 2px solid var(--primary);
      outline-offset: 2px;
    }""",
}
