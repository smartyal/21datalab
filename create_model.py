import sys
import model
import numpy
import datetime
from model import * #for the helpers


def create_test(model, testNo=1):
    if testNo == 1:
        model.create_node("root", name="variables", type="folder")
        for var in ["f0", "f1", "f2", "f3", "count", "time", "back"]:
            model.create_node("root.variables", name=var, type="column")
        model.create_node_from_path('root.folder2.myconst', {"type": "const", "value": "21data"})
        model.create_node_from_path('root.folder2.myfkt', {"type": "function"})

        # for the visu
        model.create_node_from_path('root.visualization.pipelines.demo1.url',
                                   {"type": "const", "value": "http://localhost:6001/demo1.py"})
        model.create_node_from_path('root.visualization.pipelines.demo2.url',
                                   {"type": "const", "value": "http://localhost:6002/demo2.py"})

        # create an official table
        template = [
            {
                "name": "description",
                "type": "const",
                "value": "this is a great table"
            },
            {
                "name": "columns",
                "type": "referencer",
            },
            {
                "name": "timeField",
                "type": "referencer",
            },
            {
                "name": "numberOfRows",
                "type": "variable",
                "value": 0
            }

        ]
        model.create_node("root", name="mytable", type="table")
        model.create_nodes_from_template("root.mytable", template=template)
        for var in ["f0", "f1", "f2", "f3", "time", "back"]:
            model.add_forward_refs("root.mytable.columns", ["root.variables." + var])
        model.add_forward_refs("root.mytable.timeField", ["root.variables.time"])

        # add data
        startTime = datetime.datetime(2018, 1, 1, 0, 0, 0, tzinfo=pytz.UTC)
        vars = {"f0": 0.01, "f1": 0.02, "f2": 0.04, "f3": 0.1, "back": 0.01}
        SIZE = 10 * 60  # in  seconds units
        STEP = 0.1
        # !!! we are producing size/step time points

        """ for i in range(SIZE):
            dataDict = {}
            for var in vars:
                value = numpy.cos(2*numpy.pi*vars[var]*i/SIZE*3)
                dataDict["root.variables."+var]=value
            mytime = startTime + datetime.timedelta(seconds = i)
            dataDict["root.variables.time"] = mytime
            #print(mytime)
            model.add_timeseries(dataDict)
        """

        startEpoch = date2secs(startTime)
        times = numpy.arange(startEpoch, startEpoch + SIZE, STEP, dtype=numpy.float64)
        print("we have time:", times.shape)
        for var in vars:
            values = numpy.cos(2 * numpy.pi * vars[var] * times)
            id = model.get_id("root.variables." + str(var))
            if var == "back":
                # we make -1,0,1 out of it
                values = numpy.round(values)
            model.model[id]["value"] = values.tolist()
        id = model.get_id("root.variables.time")
        model.model[id]["value"] = (1000 * times).tolist()
        # now correct the background

        # now make some widget stuff
        model.create_node_from_path('root.visualization.widgets.timeseriesOne', {"type": "widget"})
        model.create_node_from_path('root.visualization.widgets.timeseriesOne.selectableVariables',
                                   {"type": "referencer"})
        model.create_node_from_path('root.visualization.widgets.timeseriesOne.selectedVariables',
                                   {"type": "referencer"})
        model.create_node_from_path('root.visualization.widgets.timeseriesOne.startTime',
                                   {"type": "variable", "value": None})
        model.create_node_from_path('root.visualization.widgets.timeseriesOne.endTime',
                                   {"type": "variable", "value": None})
        model.create_node_from_path('root.visualization.widgets.timeseriesOne.bins',
                                   {"type": "const", "value": 300})
        model.create_node_from_path('root.visualization.widgets.timeseriesOne.hasAnnotation',
                                   {"type": "const", "value": True})
        model.create_node_from_path('root.visualization.widgets.timeseriesOne.hasSelection',
                                   {"type": "const", "value": False})
        model.create_node_from_path('root.visualization.widgets.timeseriesOne.hasAnnotation.annotations',
                                   {"type": "referencer"})
        model.create_node_from_path('root.visualization.widgets.timeseriesOne.hasAnnotation.newAnnotations',
                                   {"type": "folder"})

        model.create_node_from_path('root.visualization.widgets.timeseriesOne.hasAnnotation.tags',
                                   {"type": "const", "value": ["one", "two"]})
        model.create_node_from_path('root.visualization.widgets.timeseriesOne.hasAnnotation.colors',
                                   {"type": "const", "value": ["yellow", "brown", "greay", "green", "red"]})

        model.create_node_from_path('root.visualization.widgets.timeseriesOne.table',
                                   {"type": "referencer"})
        model.create_node_from_path('root.visualization.widgets.timeseriesOne.lineColors',
                                   {"type": "const", "value": ["blue", "yellow", "brown", "grey", "red"]})
        model.add_forward_refs('root.visualization.widgets.timeseriesOne.selectedVariables',
                              ['root.variables.f0', 'root.variables.f1', 'root.variables.f3'])
        model.add_forward_refs('root.visualization.widgets.timeseriesOne.selectableVariables', ['root.variables'])
        model.add_forward_refs('root.visualization.widgets.timeseriesOne.table', ['root.mytable'])

        model.create_node_from_path('root.visualization.widgets.timeseriesOne.observer', {"type": "referencer"})
        model.create_node_from_path('root.visualization.widgets.timeseriesOne.observerUpdate',
                                   {"type": "const", "value": ["line", "background", "annotations"]})

        # now the annotations
        anno = [
            {
                "name": "tags",
                "type": "const",
                "value": ["one", "two"]
            },
            {
                "name": "startTime",
                "type": "const",
                "value": None
            },
            {
                "name": "endTime",
                "type": "const",
                "value": None
            },
            {
                "name": "text",
                "type": "const",
                "value": "this is a great annotation"
            }

        ]

        tags = ["one", "two", "one", "one", "two", "two", "one", "one", "one", "two", "one", "one"]
        model.create_node_from_path("root.annotations", {"type": "folder"})
        startTime = datetime.datetime(2018, 1, 1, 0, 0, 0, tzinfo=pytz.UTC)
        for i in range(10):
            newAnno = copy.deepcopy(anno)
            newAnno[1]["value"] = (startTime + datetime.timedelta(minutes=(i * 10))).isoformat()
            newAnno[2]["value"] = (startTime + datetime.timedelta(minutes=(i * 10 + 1))).isoformat()
            newAnno[0]["value"] = [tags[i], tags[i + 1]]
            newAnnoPath = "root.annotations.anno" + str(i)
            model.create_node_from_path(newAnnoPath, {"type": "annotation"})
            model.create_nodes_from_template(newAnnoPath, newAnno)

        # also add the annotations to the widget
        model.add_forward_refs("root.visualization.widgets.timeseriesOne.hasAnnotation.annotations", ["root.annotations",
                                                                                                     "root.visualization.widgets.timeseriesOne.hasAnnotation.newAnnotations"])

        # make a real function
        model.create_node_from_path("root.functions", {"type": "folder"})
        model.create_nodes_from_template("root.functions", model.templates["testfunction.delayFunctionTemplate"])

        # now make cutom function to trigger something
        model.create_nodes_from_template("root.functions", model.templates["counterfunction.counterFunctionTemplate"])
        # now hook the function output to the observer of the plot
        model.add_forward_refs('root.visualization.widgets.timeseriesOne.observer',
                              ['root.functions.counterFunction.output'])

        # now make custom buttons
        buttons = [
            {
                "name": "button1",
                "type": "folder",
                "children": [
                    {"name": "caption", "type": "const", "value": "start learner"},
                    {"name": "counter", "type": "variable", "value": 0},
                    {"name": "onClick", "type": "referencer"}
                ]
            }
        ]
        model.create_node_from_path("root.visualization.widgets.timeseriesOne.buttons", {"type": "folder"})
        model.create_nodes_from_template("root.visualization.widgets.timeseriesOne.buttons", buttons)
        model.add_forward_refs("root.visualization.widgets.timeseriesOne.buttons.button1.onClick",
                              ["root.functions.counterFunction"])

        # now the backgrounds
        model.create_node_from_path("root.visualization.widgets.timeseriesOne.hasBackground",
                                   {"type": "const", "value": True})
        model.create_node_from_path("root.visualization.widgets.timeseriesOne.background", {"type": "referencer"})
        model.add_forward_refs("root.visualization.widgets.timeseriesOne.background", ["root.variables.back"])
        model.create_node_from_path("root.visualization.widgets.timeseriesOne.backgroundMap", {"type": "const",
                                                                                              "value": {"1": "red",
                                                                                                        "0": "green",
                                                                                                        "-1": "blue",
                                                                                                        "default": "white"}})

        model.show()

    elif testNo == 2:
        # we take the full test number 1 and rearrange some things
        model.create_test(1)

        import data.occupancy_data.occupancy as occ
        occData = occ.read_occupancy("./data/occupancy_data/datatest2.txt")

        # create an official table
        template = [
            {
                "name": "description",
                "type": "const",
                "value": "this is the occupancy data table"
            },
            {
                "name": "columns",
                "type": "referencer",
            },
            {
                "name": "timeField",
                "type": "referencer",
            },
            {
                "name": "variables",
                "type": "folder",
            }

        ]
        model.create_node("root", name="occupancy", type="table")
        model.create_nodes_from_template("root.occupancy", template=template)
        for var in occData:
            path = "root.occupancy.variables." + var
            model.create_node_from_path(path, {"type": "column"})
            model.set_value(path, occData[var])
            model.add_forward_refs("root.occupancy.columns", [path])
        model.add_forward_refs("root.occupancy.timeField", ["root.occupancy.variables.date"])
        # now create the classification
        model.create_node("root.occupancy", name="classification", type="column")
        model.set_value("root.occupancy.classification", [0] * len(occData[list(occData.keys())[0]]))
        model.add_forward_refs("root.occupancy.columns", ["root.occupancy.classification"])

        # create another TS-widget
        model.create_node_from_path('root.visualization.widgets.timeseriesOccupancy', {"type": "widget"})
        model.create_nodes_from_template('root.visualization.widgets.timeseriesOccupancy',
                                        modeltemplates.timeseriesWidget)
        model.create_nodes_from_template('root.visualization.widgets.timeseriesOccupancy.buttons.button1',
                                        modeltemplates.button)
        model.add_forward_refs('root.visualization.widgets.timeseriesOccupancy.selectedVariables',
                              ["root.occupancy.variables.Temperature"])
        model.add_forward_refs('root.visualization.widgets.timeseriesOccupancy.selectableVariables',
                              ["root.occupancy.variables"])
        model.add_forward_refs('root.visualization.widgets.timeseriesOccupancy.table', ['root.occupancy'])
        model.add_forward_refs('root.visualization.widgets.timeseriesOccupancy.background',
                              ['root.occupancy.classification'])

        # now create the logistic regression
        model.create_nodes_from_template('root', model.templates["logisticregression.logisticRegressionTemplate"])
        model.add_forward_refs('root.logisticRegression.input',
                              ['root.occupancy.variables.Temperature', 'root.occupancy.variables.Light',
                               'root.occupancy.variables.CO2'])
        model.add_forward_refs('root.logisticRegression.output', ['root.occupancy.classification'])
        model.add_forward_refs('root.logisticRegression.annotations',
                              ['root.visualization.widgets.timeseriesOccupancy.hasAnnotation.newAnnotations'])
        # also hook the button on it
        model.add_forward_refs('root.visualization.widgets.timeseriesOccupancy.buttons.button1.onClick',
                              ['root.logisticRegression'])

        model.add_forward_refs('root.visualization.widgets.timeseriesOccupancy.observer',
                              ['root.logisticRegression.executionCounter'])  # observe the execution of the scorer


if __name__ == '__main__':
    toCreate = sys.argv[1]
    modelName = sys.argv[2]
    
    
    myModel = model.Model()
    if toCreate == "occupancy":
        create_test(myModel,2)
    elif toCreate == "simple":
        create_test(myModel,1)

    #now save it
    myModel.save(modelName)
    