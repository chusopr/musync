import os, importlib.util, re
from types import ModuleType
from abc import abstractmethod
from sys import stderr
from PyQt5.QtCore import pyqtSignal, QObject
from appdirs import user_cache_dir

ModulesFolder = "modules"
ModuleMain = "__init__"

class SourceModule(QObject):
    __id = None
    __authenticated = False
    __read_only = False
    __session_file = os.path.join(user_cache_dir("musync"), "{}.session".format(__id))
    status = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.__id = re.sub(r"%s." % ModulesFolder, "", self.__module__)
        #@final
        self.__type = re.sub(r"%s." % ModulesFolder, "", self.__module__)
        try:
            self.__name
        except AttributeError:
            self.__name = self.__id

    def __set_session_file(self):
        self.__session_file = os.path.join(user_cache_dir("musync"), "{}.session".format(self.__id))

    def getId(self):
        return self.__id

    def setId(self, id):
        self.__id = id

    def getName(self):
        return self.__name

    def getType(self):
        return self.__type

    @abstractmethod
    def authenticate(self, force=False):
        pass

    def isReadOnly(self):
        return self.__read_only

    @abstractmethod
    def initialize(self):
        pass

    @abstractmethod
    def getPlaylists(self):
        pass

    @abstractmethod
    def getTracks(self, playlist):
        pass

    @abstractmethod
    def searchTrack(self, track):
        pass

    @abstractmethod
    def addTrack(self, playlist, track):
        pass

    def deleteAccount(self):
        if (os.path.isfile(self.__session_file)):
            os.remove(self.__session_file)

    def isAuthenticated(self):
        try:
            return self.__authenticated
        except AttributeError:
            return True

modules = {}

def create_object(mod):
        spec = importlib.util.find_spec(ModulesFolder + "." + mod)
        module = ModuleType(spec.name)
        module.__spec__ = spec
        spec.loader.exec_module(module)
        m = module.SourceModule()
        m.initialize()
        return m

def load():
    for m in os.listdir(ModulesFolder):
        m_dir = os.path.join(ModulesFolder, m)
        if not os.path.isdir(m_dir) or not os.path.isfile(os.path.join(m_dir, ModuleMain + ".py")):
            if m not in ["__init__.py", "__init__.pyc", "__pycache__"]:
                print("{} is not a valid module".format(m), file=stderr)
            continue
        spec = importlib.util.find_spec(ModulesFolder + "." + m)
        module = ModuleType(spec.name)
        module.__spec__ = spec
        spec.loader.exec_module(module)
        if not hasattr(module, "SourceModule"):
            print("{} is not a valid module".format(m), file=stderr)
            del module
            continue
        if not issubclass(module.SourceModule, SourceModule):
            # TODO: log message
            del module
            continue
        modules[m] = module.SourceModule.getName(module.SourceModule)

def listAll():
  return modules
