#21datalabplugin


from abc import ABC, abstractmethod
import utils



class Interface(ABC):

    @abstractmethod
    def flush(self,data = None):
        pass

    @abstractmethod
    def feed(self, data=None):
        pass

    @abstractmethod
    def reset(self, data=None):
        pass



class Pipeline():

    def __init__(self,processors=[]):
        self.processors=processors # these are Nodes()!

    def reset(self):
        for p in self.processors:
            p.get_object().reset()

    def feed(self,data):
        pro = utils.Profiling("pipee")
        for p in self.processors:
            pro.lap(p.get_name()+"<")
            data = p.get_object().feed(data)
            pro.lap(p.get_name()+">")
        print(pro)
        return data

    def flush(self,data):
        for p in self.processors:
            data = p.get_object().flush()
        return data





