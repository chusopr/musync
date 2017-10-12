import os, importlib.util, traceback, sys, re
from types import ModuleType

PluginsFolder = "plugins"
ModuleMain = "__init__"

plugins = {}
for p in os.listdir(PluginsFolder):
    p_dir = os.path.join(PluginsFolder, p)
    if not os.path.isdir(p_dir) or not os.path.isfile(os.path.join(p_dir, ModuleMain + ".py")):
        continue
    spec = importlib.util.find_spec(PluginsFolder + "." + p)
    module = ModuleType(spec.name)
    module.__spec__ = spec
    spec.loader.exec_module(module)
    plugins[p] = module

def listAll():
  l = {}
  for p in plugins:
    if "name" in plugins[p].__dict__:
      l[p] = plugins[p].name
    else:
      l[p] = p
  return l