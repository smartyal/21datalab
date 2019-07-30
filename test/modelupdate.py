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
        id = m.create_node_from_path(k, properties=v)
        if v["type"] == "referencer":
            #must also adjust the forward refs
            if "references" in v:
                for ref in references:
                    #the notation for references is: mytemplatename.node.node

                    newPath = '.'.join(ref.split('.')[1:])



    m.show()
    if updated:
        m.save(fileName+"_update")


def update_widgets2(fileName):
    updated = False
    m = model.Model()
    #m.disable_observers()
    m.load(fileName)
    m.disable_observers()

    # now go throught the widget and update all according the template
    # now find all type widget
    newNodes = {}
    widgets = []
    for id, props in m.model.items():
        if props["type"] == "widget":
            widgetObject = m.get_node(id)
            if widgetObject.get_child("widgetType").get_value() == "timeSeriesWidget":
                widgets.append(id)
                print("found widget @ ",widgetObject.get_browse_path())


    for id in widgets:
        path = m.get_browse_path(id)
        m.create_template_from_path(path,m.get_templates()['templates.timeseriesWidget']) # this will create all nodes which are not there yet

    m.show()
    if widgets:
        m.save(fileName + "_update")

if __name__ == '__main__':
    modelname = sys.argv[1]
    print(f"updating {modelname}")
    update_widgets2(modelname)
