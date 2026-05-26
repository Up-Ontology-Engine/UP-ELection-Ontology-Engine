import sys
import importlib.util
from importlib.abc import MetaPathFinder
from importlib.machinery import ModuleSpec

class LegacyLoader:
    def __init__(self, mod):
        self.mod = mod
    def create_module(self, spec):
        return self.mod
    def exec_module(self, module):
        pass

class LegacyRedirectFinder(MetaPathFinder):
    MAPPING = {
        'ingestion': 'pipeline.ingest',
        'etl': 'pipeline.transform',
        'nlp': 'pipeline.nlp',
        'analytics': 'pipeline.analytics',
        'flows': 'pipeline.flows',
        'graph': 'pipeline.graph',
        'db': 'pipeline.db',
        'api': 'backend'
    }

    def find_spec(self, fullname, path, target=None):
        parts = fullname.split('.')
        root = parts[0]
        if root in self.MAPPING:
            new_fullname = self.MAPPING[root]
            if len(parts) > 1:
                new_fullname += '.' + '.'.join(parts[1:])
            try:
                mod = importlib.import_module(new_fullname)
                return ModuleSpec(fullname, LegacyLoader(mod))
            except Exception:
                return None
        return None

def register():
    if not any(isinstance(f, LegacyRedirectFinder) for f in sys.meta_path):
        sys.meta_path.insert(0, LegacyRedirectFinder())
