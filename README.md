# JSONParser

Python module for extracting data from JSON using complex JSON paths.

This module contains three public objects:

 - `JSONParser`: Used to load/save JSON objects from/to files or strings.
 - `JSONPath`: Path to one or more elements of a JSON object.
 - `JSONElement`: Combines a path with an element of a JSON object.

## JSONPath syntax

A JSONPath is a string used to express an element - or set of elements - of a JSON object.

It always begins with the root character - `$` - and may be followed by any number of child elements.

Child elements can be expressed using the dot-notation or bracket–notation, or combination of both:

`$.store.book[0].title`<br/>
`$["store"]["book"][0]["title"]`<br/>
`$.store.["book"].[0].title`

### Path elements

| Element                   | Description                                                        |
| :------------------------ | :----------------------------------------------------------------- |
| `$`                       | Root - must be the first element of a JSONPath.                    |
| `.<name>`                 | Dot-notated child - <name> must match the regex [1].               |
| `["<name>"]`              | Bracket-notated child - <name> must be quoted and match regex [2]. |
| `[<index>]`               | Array index - <index> must match regex [3].                        |
| `[r"<regex>"]`            | Regex expression - <regex> must match regex [2].                   |
| `.*.` or `..`             | Search - will recursively search for first match.                  |
| `.*.*.` or `...`          | Deep search - will recursively search for all matches.             |


[1] Simple string: `[a-zA-Z_][0-9a-zA-Z_]*`<br/>
[2] Complex string: `([^"\\]|\\.)*`<br/>
[3] Array index: `[0-9]+|\*?`

### Examples

Given the following JSON object:

```
{
    "a": 1,
    "b": 2,
    "c": {
        "a": 3,
        "b": [
            "abc",
            "def",
            {
                "a": 4,
                "b": 5
            }
        ],
        "c": {
            "a": {
                "d": 6,
                "e": 7,
                "f": 8
            },
            "b": {
                "a": 9,
                "b": 10,
                "c": 11,
                "ab": {
                    "abc": "xyz"
                }
            }
        }
    }
}
```

Find below several examples of JSONPath and the matching elements:

```
JSONPath: $..a
Elements:
  $.a

JSONPath: $..ab
Elements:
  $.c.c.b.ab

JSONPath: $...a
Elements:
  $.a
  $.c.a
  $.c.b[2].a
  $.c.c.a
  $.c.c.b.a

JSONPath: $..[r"a.*"]
Elements:
  $.a

JSONPath: $..[r"a.+"]
Elements:
  $.c.c.b.ab

JSONPath: $...[r"a.+"]
Elements:
  $.c.c.b.ab
  $.c.c.b.ab.abc

JSONPath: $...[r"[a-z]{3}"]
Elements:
  $.c.c.b.ab.abc

JSONPath: $.c.b[2]
Elements:
  $.c.b[2]

JSONPath: $.c.b[]
Elements:
  $.c.b[0]
  $.c.b[1]
  $.c.b[2]

JSONPath: $.c.b[*]
Elements:
  $.c.b[0]
  $.c.b[1]
  $.c.b[2]
```

## How to use the library

```
from JSONParser import *

jsonstring = '{"a":1,"b":2,"c":{"a":3,"b":["abc","def",{"a":4,"b":5}],"c":{"a":{"d":6,"e":7,"f":8},"b":{"a":9,"b":10,"c":11,"ab":{"abc":"xyz"}}}}}'

json = JSONParser.loads(jsonstring)

for el in json.extract('$...[r"[a-z]{2,}"]'):
    print(el.path())
    print(el.object())
# $.c.c.b.ab
# {'abc': 'xyz'}
# $.c.c.b.ab.abc
# xyz

path = JSONPath()
print(path)
# $

path = path + "c" + "b"
print(path)
# $.c.b

for el in path.extract(json):
    print(el.path())
    print(el.object())
# $.c.b
# ['abc', 'def', {'a': 4, 'b': 5}]
```

## Module reference

### JSONParser.load(filename, ...) : JSONElement
`filename`: string with the filename containing the JSON data to load<br/>
`...`: additional arguments to be passed on to the underlying `json.load` function<br/>

Returns a JSONElement with the object represented by the contents of `filename` and a path of `$`.

### JSONParser.loads(string, ...) : JSONElement
`string`: string with the JSON object representation<br/>
`...`: additional arguments to be passed on to the underlying `json.loads` function<br/>

Returns a JSONElement with the object represented by the contents of `string` and a path of `$`.

### JSONParser.dump(object, filename, ...) : None
`object`: can be one of `JSONElement`, `dict`, `list`, `str`, `int`, `bool`<br/>
`filename`: string with the filename where to save the contents of `object`<br/>
`...`: additional arguments to be passed on to the underlying `json.dump` function<br/>

Writes the JSON `object` to `filename`.

### JSONParser.dumps(object, ...) : str
`object`: can be one of `JSONElement`, `dict`, `list`, `str`, `int`, `bool`<br/>
`...`: additional arguments to be passed on to the underlying `json.dumps` function<br/>

Returns a `str` with the representation of the JSON `object`.

### JSONParser.extract(object, path) : [ JSONElement, ... ]
`object`: can be one of `JSONElement`, `dict`, `list`, `str`, `int`, `bool`<br/>
`path`: can be one of `JSONPath`, `str`<br/>

Returns an array of JSONElement extracted from `object` that matched the provided `path`.

### JSONParser.matches(path1, path2) : bool
`path1`: can be one of `JSONPath`, `str`<br/>
`path2`: can be one of `JSONPath`, `str`<br/>

Returns `True` if the expansion of `path2` matches `path1`, and `False` otherwise.

---

### JSONPath.\_\_init\_\_(path=None) : JSONPath
`path`: string with a valid path (defaults to `$`)<br/>

Return a new JSONPath created from `path`.

### JSONPath.\_\_add\_\_(object) : JSONPath
`object`: can be one of `tuple`, `str`, `int`, `re.Pattern`<br/>
Tuples are used to signal for search or deep search:
 - simple tuple for search: `("obj-abc",)`
 - complex tuple for deep search: `(("obj-abc",),)`

Returns a new JSONPath with the `object` representation appended to the path.

### JSONPath.path() : str

Returns the current path as a string representation.

### JSONPath.entries(pack=True) : [ object, ... ]
`pack`: if set to `True` then the search and deep search elements will be packed in tuples.

Returns an array of objects (`str`, `int`, `re.Pattern`) representing the path elements.<br/>

### JSONPath.parent() : JSONPath

Returns a `JSONPath` representing the parent of this path.

### JSONPath.current(pack=False) : object
`pack`: if set to `True` then the search and deep search elements will be packed in tuples.

Returns the current path element.

### JSONPath.extract(object) : [ JSONElement, ... ]
`object`: can be one of `JSONElement`, `dict`, `list`, `str`, `int`, `bool`<br/>

Returns an array of JSONElement extracted from `object` using the current path.

### JSONPath.matches(path) : bool
`path`: can be one of `JSONPath`, `str`<br/>

Returns `True` if the expanded `path` matches the current path, and `False` otherwise.

---

### JSONElement.\_\_init\_\_(object, path=None) : JSONElement
`object`: can be one of `JSONElement`, `dict`, `list`, `str`, `int`, `bool`<br/>
`path`: can be one of `JSONPath`, `str` (defaults `$`)<br/>

Return a new JSONElement created from `object` and `path`.

### JSONElement.path() : JSONPath

Returns the path associated with this element.

### JSONElement.object() : object

Returns the JSON object associated with this element.

### JSONElement.key() : object

Returns the current path element.

### JSONElement.value() : object

Returns the current JSON element.

### JSONElement.extract(path) : [ JSONElement, ... ]
`path`: can be one of `JSONPath`, `str` (defaults `$`)<br/>

Returns an array of JSONElement extracted from the current object using `path`.

### JSONElement.matches(path) : bool
`path`: can be one of `JSONPath`, `str` (defaults `$`)<br/>

Returns `True` if the expanded `path` matches the current path, and `False` otherwise.

### JSONElement.json() : str

Returns the current element as a JSON string.

### JSONElement.__str__() : str

Returns the a textual representation of the current element (both path and json object).
