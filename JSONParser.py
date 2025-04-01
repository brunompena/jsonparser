import json
import re

class JSONBase(object):
    ROOT_SYMBOL        =   '$'

    CHILD              =  r'(?:(?P<child>\.(?!\.)))'
    SEARCH             =  r'(?:(?P<search>\.\*?\.(?!\.)))'
    DEEP_SEARCH        =  r'(?:(?P<deepsearch>\.\*?\.\*?\.(?!\.)))'

    NUMBER_INDEX       =  r'(?:(?P<index>[0-9]+|\*?))'
    STRING_SIMPLE      =  r'(?:(?P<string>[a-zA-Z_][0-9a-zA-Z_]*))'
    STRING_COMPLEX     =  r'(?:(?P<regex>r?)"(?P<qstring>(?:[^"\\]|\\.)*)")'

    ROOT_EXPRESSION    = fr'(?:(?P<root>\{ROOT_SYMBOL}))'
    CHILD_EXPRESSION   = fr'(?:(?:{CHILD}|{SEARCH}|{DEEP_SEARCH})?(?:{STRING_SIMPLE}|(?:\[(?:{STRING_COMPLEX}|{NUMBER_INDEX})\])))'

    PARENT_CHILD_SPLIT = fr'^(?P<parent>.+?)(?P<child>{CHILD_EXPRESSION})$'

    JSON_PATH          = fr'^{ROOT_EXPRESSION}{CHILD_EXPRESSION}*$'


    @classmethod
    def _matchesRegEx(cls, regex, path):
        return re.match(regex, path)

    @classmethod
    def _matchesRoot(cls, path):
        return cls._matchesRegEx(cls.ROOT_EXPRESSION, path)

    @classmethod
    def _matchesChild(cls, path):
        return cls._matchesRegEx(cls.CHILD_EXPRESSION, path)

    @classmethod
    def _matchesParentChild(cls, path):
        return cls._matchesRegEx(cls.PARENT_CHILD_SPLIT, path)

    @classmethod
    def _matchGetRemaidingPath(cls, match):
        return match.string[len(match.group()):]

    @classmethod
    def _matchIsSearch(cls, match):
        return ( match.group('search') is not None )

    @classmethod
    def _matchIsDeepSearch(cls, match):
        return ( match.group('deepsearch') is not None )

    @classmethod
    def _matchIsIndex(cls, match):
        return ( match.group('index') is not None and match.group('index').isdigit())

    @classmethod
    def _matchIsIndexANY(cls, match):
        return ( match.group('index') == '' or match.group('index') == '*' )

    @classmethod
    def _matchIsString(cls, match):
        return ( cls._matchGetString(match) is not None and not cls._matchIsRegex(match))

    @classmethod
    def _matchIsRegex(cls, match):
        return ( match.group('regex') == 'r' )

    @classmethod
    def _matchGetParent(cls, match):
        return match.group('parent')

    @classmethod
    def _matchGetChild(cls, match):
        return match.group('child')

    @classmethod
    def _matchGetIndex(cls, match):
        return int(match.group('index'))

    @classmethod
    def _matchGetString(cls, match):
        return ( match.group('string') or match.group('qstring') )

    @classmethod
    def _matchGetRegex(cls, match):
        return match.group('qstring')

    @classmethod
    def _pack(cls, object, search, deepsearch):
        if deepsearch:
            return ((object,),)
        elif search:
            return (object,)
        else:
            return object

    @classmethod
    def _unpack(cls, object):
        search = deepsearch = False

        while isinstance(object, tuple):
            if len(object) != 1:
                raise TypeError(f'Invalid JSON search structure: {tuple.__name__} must have exactly one element')
            else:
                object = object[0]
                deepsearch = ( search or deepsearch )
                search = ( not deepsearch )

        return object, search, deepsearch

    @classmethod
    def _entry(cls, object, search, deepsearch):
        prefix = ''
        if search:
            prefix = '..'
        elif deepsearch:
            prefix = '...'

        if isinstance(object, str):
            if re.fullmatch(cls.STRING_SIMPLE, object):
                return f'{prefix or "."}{object}'
            else:
                return f'{prefix}[{json.dumps(object)}]'

        elif isinstance(object, int):
            if object < 0:
                return f'{prefix}[*]'
            else:
                return f'{prefix}[{object}]'

        elif isinstance(object, re.Pattern):
            pattern = re.sub(r'(?<!\\)"', '\\"', object.pattern)
            return f'{prefix}[r"{pattern}"]'

    @classmethod
    def _parent(cls, path):
        match = cls._matchesParentChild(path)
        if match is not None:
            return JSONPath(cls._matchGetParent(match))
        else:
            return None

    @classmethod
    def _current(cls, path, pack):
        match = cls._matchesParentChild(path)
        if match is not None:
            match = cls._matchesChild(cls._matchGetChild(match))
            search = cls._matchIsSearch(match)
            deepsearch = cls._matchIsDeepSearch(match)

            if cls._matchIsIndex(match):
                index = cls._matchGetIndex(match)
                return cls._pack(index, search, deepsearch) if pack else index

            elif cls._matchIsIndexANY(match):
                index = -1
                return cls._pack(index, search, deepsearch) if pack else index

            elif cls._matchIsString(match):
                string = cls._matchGetString(match)
                return cls._pack(string, search, deepsearch) if pack else string

            elif cls._matchIsRegex(match):
                expr = cls._matchGetRegex(match)
                try:
                    regex = re.compile(expr)
                except:
                    raise ValueError(f'Invalid REGEX expression: {expr}') from None
                return cls._pack(regex, search, deepsearch) if pack else regex

        else:
            return cls.ROOT_SYMBOL

    @classmethod
    def _extract(cls, object, path, tracker):
        if not path:
            return [ JSONElement(object, tracker) ]

        match = cls._matchesRoot(path)
        if match is not None:
            return cls._extract(object, cls._matchGetRemaidingPath(match), tracker)

        match = cls._matchesChild(path)
        if match is not None:
            results = []

            if cls._matchIsIndex(match) and isinstance(object, list):
                index = cls._matchGetIndex(match)
                if index < len(object):
                    results.extend( cls._extract(object[index], cls._matchGetRemaidingPath(match), tracker + index) )

            elif cls._matchIsIndexANY(match) and isinstance(object, list):
                for index in range(len(object)):
                    results.extend( cls._extract(object[index], cls._matchGetRemaidingPath(match), tracker + index) )

            elif cls._matchIsString(match) and isinstance(object, dict):
                key = cls._matchGetString(match)
                if key in object:
                    results.extend( cls._extract(object[key], cls._matchGetRemaidingPath(match), tracker + key) )

            elif cls._matchIsRegex(match) and isinstance(object, dict):
                expr = cls._matchGetRegex(match)
                try:
                    regex = re.compile(expr)
                except:
                    raise ValueError(f'Invalid REGEX expression: {expr}') from None
                for key in object:
                    if regex.fullmatch(key):
                        results.extend( cls._extract(object[key], cls._matchGetRemaidingPath(match), tracker + key) )

            if (cls._matchIsSearch(match) and len(results) == 0) or cls._matchIsDeepSearch(match):
                if isinstance(object, list):
                    for index in range(len(object)):
                        results.extend( cls._extract(object[index], path, tracker + index) )
                elif isinstance(object, dict):
                    for key in object:
                        results.extend( cls._extract(object[key], path, tracker + key) )

            return results

    @classmethod
    def _matches(cls, path1, path2):
        if not any([ path1, path2 ]):
            return True
        elif not all([ path1, path2 ]):
            return False

        match1 = cls._matchesRoot(path1)
        match2 = cls._matchesRoot(path2)
        if match1 is not None and match2 is not None:
            return cls._matches(cls._matchGetRemaidingPath(match1), cls._matchGetRemaidingPath(match2))

        match1 = cls._matchesChild(path1)
        match2 = cls._matchesChild(path2)
        if match1 is not None and match2 is not None:
            result = None

            if cls._matchIsIndex(match1) and cls._matchIsIndex(match2):
                if cls._matchGetIndex(match1) == cls._matchGetIndex(match2):
                    result = cls._matches(cls._matchGetRemaidingPath(match1), cls._matchGetRemaidingPath(match2))

            elif cls._matchIsIndexANY(match1) and cls._matchIsIndex(match2):
                result = cls._matches(cls._matchGetRemaidingPath(match1), cls._matchGetRemaidingPath(match2))

            elif cls._matchIsIndexANY(match1) and cls._matchIsIndexANY(match2):
                result = cls._matches(cls._matchGetRemaidingPath(match1), cls._matchGetRemaidingPath(match2))

            elif cls._matchIsString(match1) and cls._matchIsString(match2):
                if cls._matchGetString(match1) == cls._matchGetString(match2):
                    result = cls._matches(cls._matchGetRemaidingPath(match1), cls._matchGetRemaidingPath(match2))

            elif cls._matchIsRegex(match1) and cls._matchIsString(match2):
                expr = cls._matchGetRegex(match1)
                try:
                    regex = re.compile(expr)
                except:
                    raise ValueError(f'Invalid REGEX expression: {expr}') from None
                if regex.fullmatch(cls._matchGetString(match2)) is not None:
                    result = cls._matches(cls._matchGetRemaidingPath(match1), cls._matchGetRemaidingPath(match2))

            elif cls._matchIsRegex(match1) and cls._matchIsRegex(match2):
                if cls._matchGetRegex(match1) == cls._matchGetRegex(match2):
                    result = cls._matches(cls._matchGetRemaidingPath(match1), cls._matchGetRemaidingPath(match2))

            if ((result is None) and cls._matchIsSearch(match1)) or ((result != True) and cls._matchIsDeepSearch(match1)):
                result = cls._matches(path1, cls._matchGetRemaidingPath(match2))

            return bool(result)


class JSONParser(JSONBase):
    @staticmethod
    def load(filename, *args, **kwargs):
        with open(filename, 'r') as file:
            return JSONElement(json.load(file, *args, **kwargs))

    @staticmethod
    def loads(string, *args, **kwargs):
        return JSONElement(json.loads(string, *args, **kwargs))

    @staticmethod
    def dump(object, filename, *args, **kwargs):
        with open(filename, 'w+') as file:
            if isinstance(object, JSONElement):
                json.dump(object.object(), file, *args, **kwargs)
            else:
                json.dump(object, file, *args, **kwargs)

    @staticmethod
    def dumps(object, *args, **kwargs):
        if isinstance(object, JSONElement):
            return json.dumps(object.object(), *args, **kwargs)
        else:
            return json.dumps(object, *args, **kwargs)

    @classmethod
    def extract(cls, object, path):
        if isinstance(object, JSONElement):
            return cls._extract(object.object(), JSONPath(path), JSONPath(object.path()))
        else:
            return cls._extract(object, JSONPath(path), JSONPath())

    @classmethod
    def matches(cls, path1, path2):
        return cls._matches(JSONPath(path1), JSONPath(path2))


class JSONPath(JSONBase, str):
    def __new__(cls, path=None):
        if path is not None and not isinstance(path, (str, JSONPath)):
            raise TypeError(f'Invalid JSON path type: {type(path).__name__} (expected: None, {str.__name__} or {JSONPath.__name__})')
        elif path is None or not path:
            path = cls.ROOT_SYMBOL

        if re.match(cls.JSON_PATH, path) is None:
            raise ValueError(f'Invalid JSON path syntax: {path}')
        else:
            return super().__new__(cls, path)

    def __add__(self, object):
        object, search, deepsearch = self._unpack(object)
        if not isinstance(object, (tuple, str, int, re.Pattern)):
            raise TypeError(f'Invalid JSON key type: {type(object).__name__} (expected: {tuple.__name__}, {str.__name__}, {int.__name__} or {re.Pattern.__name__})')
        else:
            return JSONPath(str(self) + self._entry(object, search, deepsearch))

    def path(self):
        return self

    def entries(self, pack=True):
        entries = []
        cursor = self
        while cursor is not None:
            entries.append(cursor.current(pack=pack))
            cursor = cursor.parent()
        return entries[::-1]

    def parent(self):
        return self._parent(self)

    def current(self, pack=False):
        return self._current(self, pack)

    def extract(self, object):
        if isinstance(object, JSONElement):
            return self._extract(object.object(), self, object.path())
        else:
            return self._extract(object, self, JSONPath())

    def matches(self, path):
        return self._matches(self, JSONPath(path))


class JSONElement(JSONBase):
    def __init__(self, object, path=None):
        if object is not None and not isinstance(object, (JSONElement, dict, list, str, int, bool)):
            raise TypeError(f'Invalid JSON object type: {type(object).__name__} (expected: {JSONElement.__name__}, {dict.__name__}, {list.__name__}, {str.__name__}, {int.__name__}, {bool.__name__} or None)')
        elif isinstance(object, JSONElement):
            self._object = object.object()
            self._path = JSONPath(path or object.path())
        else:
            self._object = object
            self._path = JSONPath(path)

    def path(self):
        return self._path

    def object(self):
        return self._object

    def key(self):
        return self._path.current()

    def value(self):
        return self._object

    def extract(self, path):
        return self._extract(self._object, JSONPath(path), self._path)

    def matches(self, path):
        return self._matches(self._path, JSONPath(path))

    def json(self):
        return json.dumps(self._object, indent=4)

    def __str__(self):
        return f'{self._path}\n{self.json()}'


__all__ = ['JSONParser', 'JSONPath', 'JSONElement']

