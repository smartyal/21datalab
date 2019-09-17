

import model
import time

def test_model_api():
    m=model.Model()
    m.create_node_from_path("root.myfolder.myvariable")
    m.create_node_from_path("root.myfolder.myvariable2")
    m.create_node_from_path("root.myfolder.myvariable3")
    m.create_node_from_path("root.myfolder2.x")
    m.create_node_from_path("root.myfolder2.y")
    m.create_node_from_path("root.myfolder2.z")

    m.create_node_from_path("root.newvar")
    m.set_value("root.newvar",1234.44556)




    time.sleep(1)
    m.show()

def test_node_api():
    m = model.Model()
    m.create_node_from_path("root.myfolder.myvariable")
    m.create_node_from_path("root.myfolder.myvariable2")
    m.create_node_from_path("root.myfolder.myvariable3")
    res1 = m.create_node_from_path("root.myfolder2.x")
    res2 = m.create_node_from_path("root.myfolder2.x")
    print(f"res1{res1} res2{res2}")
    m.create_node_from_path("root.myfolder2.y")
    m.create_node_from_path("root.myfolder2.z")
    m.get_value("root.myfolder2.z")
    nodeid = m.get_id("root.myfolder2.z")
    m.get_value(nodeid)

    n=m.get_node("root.myfolder2") #  n is an object of Node()

    #nodeapi
    n.set_value("dfg")
    x = n.get_child("x")
    x.set_value("api test")

    val = x.get_value()
    print(f"val:{val}")


if __name__ == "__main__":
    #test_model_api()
    test_node_api()