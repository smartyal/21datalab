from system import __functioncontrolfolder
import logging


label_editor_template = {
    "name": "label_editor",
    "type": "folder",
    "children": [
        { "name": "cockpit", "type": "const", "value": "customui/label_editor/index.htm"},
        { "name": "master_frontend", "type": "referencer"},
        { "name": "slave_frontends", "type": "referencer"},
    ]
}
