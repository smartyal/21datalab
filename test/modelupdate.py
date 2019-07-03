import sys
sys.path.append('..')
sys.path.append('../plugins')

import model
import modeltemplates

def update_widgets(fileName):
    updated = False
    m=model.Model()
    temp = m.get_templates()
    m.load(fileName)
    #now go throught the widget and update all according the template
    #now find all type widget
    newNodes ={}
    for id,props in m.model.items():
        if props["type"] == "widget":
            widget = m.get_node(id)
            print("found widget ",widget.get_browse_path())
            #now go through all first level properties and bring them in if they are missing
            for entry in m.get_templates()['templates.timeseriesWidget']["children"]:
                name = entry["name"]
                if not widget.get_child(name):
                    updated = True
                    print("missing " +name + " in "+widget.get_browse_path())
                    newNodes[widget.get_browse_path()+"."+name]=entry

    for k,v in newNodes.items():
        m.create_node_from_path(k, properties=v)
    m.show()
    if updated:
        m.save(fileName+"_update")

if __name__ == '__main__':
    modelname = sys.argv[1]
    print(f"updating {modelname}")
    update_widgets(modelname)
