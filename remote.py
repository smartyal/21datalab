import model
import requests
import time
import datetime
import json
import copy
import numpy





class ModelRestClient():

    def __init__(self,url,logger):
        self.url = url
        self.restTimeout = 50
        self.proxySetting = None
        self.logger = logger


    def request(self,method="GET",path="",reqData={}):
        """
            this functions makes a call to the backend model serer to get data
            Args:
                method(string) one of ["GET","POST"]
                path: the nodepath to the time series widtet
                reqData: a dictionary with request data for te query like the list of variables, time limits etc.
            Returns (dict):
                the data from the backend as dict
        """
        self.logger.info("__web_call: %s %s %s",method,path,str(reqData))

        response = None
        now = datetime.datetime.now()
        if method.upper() == "GET":
            try:
                response = requests.get(self.url + path, timeout=self.restTimeout,proxies=self.proxySetting)
            except Exception as ex:
                self.logger.error("requests.get msg:"+str(ex))

        elif method.upper() == "POST":
            now = datetime.datetime.now()
            try:
                response = requests.post(self.url + path, data=json.dumps(reqData), timeout=self.restTimeout,
                                         proxies=self.proxySetting)
            except Exception as ex:
                self.logger.error("requets.post  msg:" + str(ex))

        after = datetime.datetime.now()
        diff = (after-now).total_seconds()
        self.logger.info(f"response {response} on {method} {path} took {diff}s ")
        if not response:
            self.logger.error("Error calling web " + path )
            return None
        else:
            rData = json.loads(response.content.decode("utf-8"))
            return rData


class RemoteModel(model.Model):

    def __init__(self,remoteUrl, localModel=None,logger=None):
        model.Model.__init__(self)
        self.disable_observers() #  no active elements in the remote model

        self.remoteUrl = remoteUrl
        self.getValuesSeparate = False
        self.rest = ModelRestClient(self.remoteUrl,self.logger)

    def __diff(self,remoteModel,localModel):
        """
            check the diff between local and remote, always get the latest remote
            Args:
                remoteModel: dict of nodes
                localModel: dict of nodes


            Returns: dict
                "additional": the nodes which are additional in the local
                "missing": the nodes which are missing in the local, so they are additional in remote
                "modified": nodes which are on both sides, but are not equal

        """

        additionalNodeIds =   list( set(localModel.keys()) - set(remoteModel.keys()) )
        missingNodeIds =      list( set(remoteModel.keys()) - set(localModel.keys()) )
        modifiedNodesIds = []
        bothNodeIds = list(set(localModel.keys()) -  set(additionalNodeIds) - set(missingNodeIds))
        for id in bothNodeIds:
            localNodeSerialized = json.dumps(localModel[id], sort_keys=True)
            remoteNodeSerialized = json.dumps(remoteModel[id], sort_keys=True)
            if localNodeSerialized != remoteNodeSerialized:
                #something is different
                modifiedNodesIds.append(id)
        return {"additional":additionalNodeIds,"missing":missingNodeIds,"modified":modifiedNodesIds}


    def pull_branch(self, branchRoot):
        """
            get remote nodes including values  and bring them into the local model
            we make a synchronization:
                - existing nodes will get fresh properties and value
                - additional nodes will be created
                - nodes that we have locally but not remote will be deleted
            the process is:
                - we delete all local nodes under the given root, we get all remote nodes and copy them into the local model

            Args:
                remoteBranchRoot: string : the remote branch node under which we take all nodes

            Return

        """
        self.logger.debug(f"pull remote {self.remoteUrl} -- {branchRoot}")
        remoteNodes = self.rest.request(path="_getallhashed")
        localNodes= self.get_model_for_web(getHash=True)

        # 1) delete the local nodes which are gone in the remote (only for branch-style relevant)
        #       we try to be clever to avoid to rip of local references, so we only delete whats necessary
        #       so make a diff and see whats missing in remote
        # 2) get the remotenodes


        remoteModel = model.Model()     #helper object
        remoteModel.model=remoteNodes   # all remote nodes are applied to the model

        remoteBranch = remoteModel.get_branch(branchRoot,includeRoot=False,includeForwardRefs=False)
        localBranch = self.get_branch(branchRoot,includeRoot=False,includeForwardRefs=False)

        onlyLocalNodeIds = list (set(localBranch.keys()) - set(remoteBranch.keys()))
        if onlyLocalNodeIds:
            self.logger.debug("must delete some local nodes which are not in the remote")
            for id in onlyLocalNodeIds:
                self.delete_node(id)


        #now check the diffs
        nodesFilter = list(remoteBranch.keys())

        mustUpdate  = []  # a list of nodeids of which we should update the values
        diff = self.__diff(remoteNodes,localNodes)
        self.logger.debug(f"diff remote and local: diff{diff}")
        if diff["missing"]:
            # these nodes are in the remote and not in the local, we must bring them in
            newRemoteNodes=[id for id in diff["missing"] if id in nodesFilter]
            if newRemoteNodes:
                self.logger.info(f"new remote nodes to add {[remoteNodes[id]['browsePath'] for id in newRemoteNodes]}")
                self.__copy_nodes_from_remote(newRemoteNodes,remoteNodes,withValues=True)
        if diff["modified"]:
            modifiedNodes =[id for id in diff["modified"] if id in nodesFilter]
            if modifiedNodes:
                self.logger.debug(f"modifiedNodes to load {[remoteNodes[id]['browsePath'] for id in modifiedNodes]}")
                self.__copy_nodes_from_remote(modifiedNodes, remoteNodes, withValues=True)


    def pull_values(self,remoteNodes):
        """
            get the values of remote nodes (either from all nodes of a branch or a list of nodes)
            Args:  remoteNodes:
            Returns:

        """
        self.logger.info(f"@ pull_values {remoteNodes}")
        data = self.rest.request("POST", "_getvalue", remoteNodes)
        for id, array in zip(remoteNodes, data):
            self.set_value(id, array)

    def push_branch(self,branchRoot):
        """
            push all nodes to the remote including value under the branchRoot
            1) see if we have to delete nodes in the remote
            2) push all nodes to remote
            3) push all value of column, files to remote

        """
        self.logger.debug(f"push remote {self.remoteUrl} -- {branchRoot}")

        remoteNodes = self.rest.request(path="_getallhashed")
        localNodes = self.get_model_for_web(getHash=True)

        remoteModel = model.Model()  # helper object
        remoteModel.model = remoteNodes  # all remote nodes are applied to the model

        remoteBranch = remoteModel.get_branch(branchRoot, includeRoot=False, includeForwardRefs=False)
        localBranch = self.get_branch(branchRoot, includeRoot=False, includeForwardRefs=False)

        #delete the nodes in remote that are not in the local
        onlyRemoteNodeIds = list(set(localBranch.keys()) - set(localBranch.keys()))
        if onlyRemoteNodeIds:
            self.logger.debug(f"must delete some local nodes which are not in the local {onlyRemoteNodeIds}")
            self.rest.request("POST","_delete",onlyRemoteNodeIds)


        # now check the diffs
        nodesFilter = list(localBranch.keys())

        mustUpdate = []  # a list of nodeids of which we should update the values
        diff = self.__diff(remoteNodes, localNodes)
        self.logger.debug(f"diff remote and local: diff{diff}")

        nodeIdsToPush = []

        nodeIdsToPush.extend(diff["additional"])
        nodeIdsToPush.extend(diff["modified"])

        #now filter only the relevant ones
        newRemoteNodeIds = [id for id in nodeIdsToPush if id in nodesFilter]
        self.logger.debug(f"pushing nodes to remote {newRemoteNodeIds}")

        #if the branch was just created, we need to push the parent as well to update the child info
        branchRootId = self.get_id(branchRoot)
        parentId = self.model[branchRootId]["parent"]
        if parentId != 0:
            newRemoteNodeIds.append(parentId)
        #now push them
        body = [localNodes[id] for id in newRemoteNodeIds]
        if body:
            self.rest.request("POST","_push",body)

    def __copy_nodes_from_remote(self,nodeIds,remoteNodes,withValues=True):
        """
            copy nodes and also get (REST) values if needed (columns, files)

        """
        if not remoteNodes or not nodeIds:
            return
        self.logger.debug(f"copy nodes from remote {nodeIds} with value {withValues}")
        valueIds = []
        for id in nodeIds:
            self.model[id]=copy.deepcopy(remoteNodes[id])
            if withValues and remoteNodes[id]["type"] in ["column","file"]:
                valueIds.append(id)
                #we also need to get the values
        if valueIds:
            self.logger.debug(f"now get the remote values for {valueIds}")
            if not self.getValuesSeparate:
                data = self.rest.request("POST","_getvalue",valueIds)
                for id,array in zip(valueIds,data):
                    self.set_value(id,array)
            else:
                for id in valueIds:
                    data = self.rest.request("POST","_getvalue",[id])
                    self.set_value(id,data)


    def push_values(self, nodeIds):
        """

            Args:  remoteNodes:
            Returns:

        """
        self.logger.info(f"@ push_values {nodeIds}")
        body = []
        for nodeid in nodeIds:
            value = self.get_value(nodeid)
            if type(value) is numpy.ndarray:
                value = list(value)
            node = {"id":nodeid,"value":value}
            body.append(node)
        self.rest.request("POST", "setProperties", body)


def test1():
    print("make a test")

    m=model.Model()
    #m.load('occupancydemo')
    r=Remote("http://127.0.0.1:6001/",m,m.logger)
    m.create_node_from_path("root.test")

    r.pull_branch("root")
    #r.pull_values(["126"])
    m.show()


def test2():

    m=RemoteModel("http://127.0.0.1:6001/")
    m.load('occupancydemo')
    #r=Remote("http://127.0.0.1:6001/",m,m.logger)
   # m.create_node_from_path("root.test")

    m.pull_branch("root.occupancyData")
    #r.pull_values(["126"])
    #m.show()

def push_test1():
    m = RemoteModel("http://127.0.0.1:6001/")
    m.pull_branch("root")
    #m.load('occupancydemo')
    #m.create_node_from_path("root.test")
    #m.push_branch('root')
    #time.sleep(5)
    #m.create_node_from_path("root.test")

    m.create_node_from_path("root.test.a.b.c.d")
    #m.create_node_from_path("root.myextra")
    m.push_branch('root.test')

def push_test2():
    m=RemoteModel("http://127.0.0.1:6001/")
    m.pull_branch("root")
    no = m.get_node("root.occupancyData.classification")
    no.set_value([0]*len(no.get_value()))
    m.push_values([no.get_id()])

    #now change something
    val = no.get_value()
    val[1]=2
    no.set_value(val)
    m.pull_branch("root.occupancyData")

def modify_test():
    m = RemoteModel("http://127.0.0.1:6001/")
    m.pull_branch("root")

def full_load_test():
    m = RemoteModel("http://127.0.0.1:6001/")
    m.getValuesSeparate = True
    m.pull_branch("root")


if __name__ == '__main__':
    full_load_test()

