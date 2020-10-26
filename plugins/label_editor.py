from system import __functioncontrolfolder
import logging


label_editor_template = {
    "name": "label_editor",
    "type": "folder",
    "children": [
        { "name": "cockpit", "type": "const", "value": "customui/label_editor/index.htm"},
        { "name": "src_frontends", "type": "referencer"},
        { "name": "dst_frontends", "type": "referencer"},
    ]
}
