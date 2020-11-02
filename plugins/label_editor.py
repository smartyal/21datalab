from system import __functioncontrolfolder
import logging


label_editor_template = {
    "name": "label_editor",
    "type": "folder",
    "children": [
        { "name": "cockpit", "type": "const", "value": "customui/label_editor/index.htm"},
        # frontend from which existing tags are read
        { "name": "master_frontend", "type": "referencer"},
        # frontends to which updated tags are written
        { "name": "slave_frontends", "type": "referencer"},
        # annotations which should be updated
        {"name": "annotations", "type": "referencer"},
    ]
}
