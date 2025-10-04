"""
UI-TARS Action Configuration
Based on: https://github.com/bytedance/UI-TARS/blob/main/codes/ui_tars/action_parser.py
"""

# Action configuration schema
ACTION_CONFIG = {
    "click": {
        "description": "Single left click",
        "fields": [
            {"name": "x", "type": "coordinate", "label": "X coordinate", "placeholder": "1710"},
            {"name": "y", "type": "coordinate", "label": "Y coordinate", "placeholder": "100"}
        ],
        "template": lambda params: f"click(point='<point>{params['x']} {params['y']}</point>')"
    },

    "left_double": {
        "description": "Double left click",
        "fields": [
            {"name": "x", "type": "coordinate", "label": "X coordinate", "placeholder": "1710"},
            {"name": "y", "type": "coordinate", "label": "Y coordinate", "placeholder": "100"}
        ],
        "template": lambda params: f"left_double(point='<point>{params['x']} {params['y']}</point>')"
    },

    "right_single": {
        "description": "Single right click",
        "fields": [
            {"name": "x", "type": "coordinate", "label": "X coordinate", "placeholder": "1710"},
            {"name": "y", "type": "coordinate", "label": "Y coordinate", "placeholder": "100"}
        ],
        "template": lambda params: f"right_single(point='<point>{params['x']} {params['y']}</point>')"
    },

    "hover": {
        "description": "Hover over element",
        "fields": [
            {"name": "x", "type": "coordinate", "label": "X coordinate", "placeholder": "1710"},
            {"name": "y", "type": "coordinate", "label": "Y coordinate", "placeholder": "100"}
        ],
        "template": lambda params: f"hover(point='<point>{params['x']} {params['y']}</point>')"
    },

    "type": {
        "description": "Type text",
        "fields": [
            {"name": "content", "type": "text", "label": "Text to type", "placeholder": "Hello World"}
        ],
        "template": lambda params: f"type(content='{params['content']}')"
    },

    "hotkey": {
        "description": "Keyboard shortcut (space-separated)",
        "fields": [
            {"name": "key", "type": "text", "label": "Key combination", "placeholder": "ctrl c"}
        ],
        "template": lambda params: f"hotkey(key='{params['key']}')"
    },

    "press": {
        "description": "Press single key",
        "fields": [
            {"name": "key", "type": "text", "label": "Key name", "placeholder": "enter"}
        ],
        "template": lambda params: f"press(key='{params['key']}')"
    },

    "keydown": {
        "description": "Press and hold key",
        "fields": [
            {"name": "key", "type": "text", "label": "Key name", "placeholder": "shift"}
        ],
        "template": lambda params: f"keydown(key='{params['key']}')"
    },

    "keyup": {
        "description": "Release key",
        "fields": [
            {"name": "key", "type": "text", "label": "Key name", "placeholder": "shift"}
        ],
        "template": lambda params: f"keyup(key='{params['key']}')"
    },

    "drag": {
        "description": "Drag from start to end",
        "fields": [
            {"name": "x1", "type": "coordinate", "label": "Start X", "placeholder": "100"},
            {"name": "y1", "type": "coordinate", "label": "Start Y", "placeholder": "100"},
            {"name": "x2", "type": "coordinate", "label": "End X", "placeholder": "500"},
            {"name": "y2", "type": "coordinate", "label": "End Y", "placeholder": "500"}
        ],
        "template": lambda params: f"drag(start_point='<point>{params['x1']} {params['y1']}</point>', end_point='<point>{params['x2']} {params['y2']}</point>')"
    },

    "select": {
        "description": "Select/highlight area",
        "fields": [
            {"name": "x1", "type": "coordinate", "label": "Start X", "placeholder": "100"},
            {"name": "y1", "type": "coordinate", "label": "Start Y", "placeholder": "100"},
            {"name": "x2", "type": "coordinate", "label": "End X", "placeholder": "500"},
            {"name": "y2", "type": "coordinate", "label": "End Y", "placeholder": "500"}
        ],
        "template": lambda params: f"select(start_point='<point>{params['x1']} {params['y1']}</point>', end_point='<point>{params['x2']} {params['y2']}</point>')"
    },

    "scroll": {
        "description": "Scroll in direction",
        "fields": [
            {"name": "x", "type": "coordinate", "label": "X coordinate", "placeholder": "800"},
            {"name": "y", "type": "coordinate", "label": "Y coordinate", "placeholder": "600"},
            {"name": "direction", "type": "select", "label": "Direction", "options": ["up", "down", "left", "right"], "default": "down"},
            {"name": "pixels", "type": "text", "label": "Pixels", "placeholder": "100"}
        ],
        "template": lambda params: f"scroll(point='<point>{params['x']} {params['y']}</point>', direction='{params['direction']}', pixels={params.get('pixels', '100')})"
    },

    "finished": {
        "description": "Task completed",
        "fields": [
            {"name": "content", "type": "text", "label": "Completion message", "placeholder": "Task completed successfully"}
        ],
        "template": lambda params: f"finished(content='{params['content']}')"
    }
}


def parse_coordinates(coord_input):
    """
    Parse coordinate input in various formats:
    - "38,38" -> ("38", "38")
    - "38 38" -> ("38", "38")
    - "38" -> ("38", None)
    """
    if ',' in coord_input:
        parts = coord_input.split(',')
        return parts[0].strip(), parts[1].strip() if len(parts) > 1 else None
    elif ' ' in coord_input:
        parts = coord_input.split()
        return parts[0].strip(), parts[1].strip() if len(parts) > 1 else None
    else:
        return coord_input.strip(), None


def build_action(action_type, params):
    """Build action string from type and parameters"""
    if action_type not in ACTION_CONFIG:
        return f"{action_type}(...)"

    config = ACTION_CONFIG[action_type]

    # Validate all required fields are present
    for field in config["fields"]:
        if field["name"] not in params or not params[field["name"]]:
            return None

    return config["template"](params)
