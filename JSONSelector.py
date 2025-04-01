#!/usr/bin/python3 -B

import argparse

from JSONParser import JSONParser

class JSONSelector:
    def __init__(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('filename', metavar='FILE', action='store', help='JSON filename')
        parser.add_argument('selector', metavar='SELECTOR', action='store', help='JSONPath selector')
        self.args = parser.parse_args()

    def run(self):
        for element in JSONParser.load(self.args.filename).extract(self.args.selector):
            print(element)
            print()

if __name__== '__main__':
    JSONSelector().run()
