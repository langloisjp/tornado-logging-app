import unittest
import doctest
import tornadoutil

def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(tornadoutil))
    return tests

