#!/usr/bin/python3 -B

import argparse
import re

from JSONParser import JSONParser, JSONPath, JSONElement

class JSONCompare:
    class _ExtendAction(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            items = getattr(namespace, self.dest) or []
            for value in values if isinstance(values, list) or isinstance(values, tuple) else [ values ]:
                if value not in items:
                    items.append(value)
            setattr(namespace, self.dest, items)

    def __init__(self):
        parser = argparse.ArgumentParser()
        parser.register('action', 'extend', self._ExtendAction)
        parser.add_argument('file1', metavar='FILE1', action='store', help='Filename of the old/left JSON')
        parser.add_argument('file2', metavar='FILE2', action='store', help='Filename of the new/right JSON')
        parser.add_argument('-s', '--selector', dest='selectors', metavar='SELECTOR', nargs='*', default=[], action='extend', help='List of JSONPath selectors (default: $)')
        parser.add_argument('-m', '--mapping', dest='mappings', metavar='MAPPING', nargs='*', default=[], action='extend', help='List of mappings in the format: JSONPath=keyid (default: none)')
        parser.add_argument('-i', '--ignore', dest='ignores', metavar='IGNORE', nargs='*', default=[], action='extend', help='List of JSONPath to be ignored (default: none)')
        self.args = parser.parse_args()

    def _loadJSONFiles(self):
        self._json1 = JSONParser.load(self.args.file1)
        self._json2 = JSONParser.load(self.args.file2)

    def _processSelectors(self):
        if len(self.args.selectors) > 0:
            self._elements1 = { element.path() : element.object() for selector in self.args.selectors for element in self._json1.extract(selector) }
            self._elements2 = { element.path() : element.object() for selector in self.args.selectors for element in self._json2.extract(selector) }
        else:
            self._elements1 = { self._json1.path() : self._json1.object() }
            self._elements2 = { self._json2.path() : self._json2.object() }

    def _processMappings(self):
        self._mappings = {}
        for mapping in self.args.mappings:
            match = re.match(r'^(?P<path>.+)=(?P<keyid>[^=]+)$', mapping)
            if match:
                self._mappings[JSONPath(match.group('path'))] = match.group('keyid')
            else:
                raise ValueError(f'Invalid mapping syntax: {mapping}')

    def _processIgnores(self):
        self._ignores = {}
        for ignore in self.args.ignores:
            match = re.match(r'^(?P<path>.+)\{(?P<evalop>.+)\}$', ignore)
            if match:
                self._ignores[JSONPath(match.group('path'))] = match.group('evalop')
            else:
                self._ignores[JSONPath(ignore)] = None

    def _compareJSONElements(self):
        paths = list(self._elements1.keys())
        paths.extend([ path for path in self._elements2.keys() if path not in paths ])
        for path in paths:
            self._compare(self._elements1.get(path, None), self._elements2.get(path, None), path)

    def _logWarning(self, message):
        print(f'[WARNING] {message}')
        print()

    def _logDifference(self, path, separator, value1, value2):
        print(f'-{path} {separator} {value1}')
        print(f'+{path} {separator} {value2}')
        print()

    def _typetoJSON(self, object):
        if isinstance(object, dict):
            return 'object'
        elif isinstance(object, list):
            return 'array'
        elif isinstance(object, str):
            return 'string'
        elif isinstance(object, int):
            return 'number'
        elif isinstance(object, bool):
            return 'boolean'
        elif object is None:
            return 'null'

    def _findMapping(self, path):
        for mapping, keyid in self._mappings.items():
            if mapping.matches(path):
                return keyid

    def _ignoreElement(self, path, value1=None, value2=None):
        for ignore, evalop in self._ignores.items():
            if ignore.matches(path):
                if evalop is None:
                    return True
                elif all([evalop is not None, value1 is not None, value2 is not None]):
                    if evalop == '>':
                        return value1 > value2
                    elif evalop == '<':
                        return value1 < value2
                    else:
                        raise NotImplementedError(f'The evaluation operator {evalop} is not implemented.')
        return False

    def _compare(self, object1, object2, path):
        if not any([ object1, object2 ]) or self._ignoreElement(path):
            return
        elif object1 is None:
            self._logDifference(path, ':', '<null>', f'[{self._typetoJSON(object2)}]')
        elif object2 is None:
            self._logDifference(path, ':', f'[{self._typetoJSON(object1)}]', '<null>')
        elif type(object1) is not type(object2):
            self._logDifference(path, ':', f'[{self._typetoJSON(object1)}]', f'[{self._typetoJSON(object2)}]')
        elif isinstance(object1, int) or isinstance(object1, str) or isinstance(object1, bool):
            if object1 != object2 and not self._ignoreElement(path, object1, object2):
                self._logDifference(path, '=', JSONParser.dumps(object1), JSONParser.dumps(object2))
        elif isinstance(object1, dict):
            keys = list(object1.keys())
            keys.extend([ key for key in object2.keys() if key not in keys ])
            for key in keys:
                self._compare(object1.get(key, None), object2.get(key, None), path + key)
        elif isinstance(object1, list):
            #TODO: check object2 values against object1
            for index1 in range(len(object1)):
                value1 = object1[index1]
                if isinstance(value1, dict):
                    keyid = self._findMapping(path)
                    if keyid is not None:
                        if keyid in value1:
                            for index2 in range(len(object2)):
                                value2 = object2[index2]
                                if isinstance(value2, dict):
                                    if keyid in value2:
                                        if value1[keyid] == value2[keyid]:
                                            self._compare(value1, value2, path + index1)
                                    else:
                                        self._logWarning(f'Mapping error on JSON2: {path}={keyid}  (skipping)')
                        else:
                            self._logWarning(f'Mapping error on JSON1: {path}={keyid}  (skipping)')
                    else:
                        self._logWarning(f'Mapping is missing for: {path}  (skipping)')
                elif isinstance(object1[index1], list):
                    self._logWarning(f'Multidimensional arrays are not supported: {path}  (skipping)')
                elif object1[index1] not in object2:
                    self._logDifference(path + index1, '=', JSONParser.dumps(object1[index1]), '<null>')
        else:
            raise TypeError(f'Unexpected object type found: {type(object1)}')

    def run(self):
        self._loadJSONFiles()
        self._processSelectors()
        self._processMappings()
        self._processIgnores()
        self._compareJSONElements()


if __name__== '__main__':
    JSONCompare().run()

