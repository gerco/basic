#!/usr/bin/python

'''
Documentation, License etc.

@package basic
'''

import sys
import os
from dataclasses import dataclass
from typing import List

operators = ["+", "-", "/", "*", "=", "&"]
variables = {}

class Lookahead():
     "Wrap iterator with lookahead to both peek and test exhausted"

     _NONE = object()
     def __init__(self, iterable):
         self._it = iter(iterable)
         self._set_peek()
     def __iter__(self):
         return self
     def __next__(self):
         if self.peek == self._NONE:
             raise StopIteration
         ret = self.peek
         self._set_peek()
         return ret
     def _set_peek(self):
         try:
             self.peek = next(self._it)
         except StopIteration:
             self.peek = self._NONE
     def __bool__(self):
         return self.peek is not self._NONE

@dataclass
class Token: 
    line: int
    pos: int
    value: str
    def __eq__(self, other):
        if isinstance(other, str):
            return self.value.lower() == other.lower()
        else:
            return False
    
    def __str__(self):
        return "'%s' at line %d, pos %d" % (self.value, self.line, self.pos)

@dataclass
class StringToken(Token):
    def __eq__(self, other):
        return False;

class Node:
    pass

class Statement(Node):
    pass

@dataclass
class Statements(Node):
    statements: List[Statement]
    def exec(self):
        for stmt in self.statements:
            stmt.exec()

class Expression(Node):
    pass

@dataclass
class Number(Expression):
    value: float
    def __init__(self, value):
        self.value = float(value)
    def eval(self):
        return self.value;
    
@dataclass
class String(Expression):
    value: str
    def eval(self):
        return self.value

@dataclass
class Variable(Expression):
    name: str
    def eval(self):
        return variables[self.name]

@dataclass
class If(Statement):
    expr: Expression
    thenDo: Statement
    elseDo: Statement
    def exec(self):
        if(self.expr.eval()):
            self.thenDo.exec()
        else:
            self.elseDo.exec()

@dataclass            
class For(Statement):
    varname: str
    initialValue: Expression
    finalValue: Expression
    body: Statements
    
    def exec(self):
        variables[self.varname] = self.initialValue.eval()
        while variables[self.varname] <= self.finalValue.eval():
            self.body.exec()
            variables[self.varname] += 1
            
@dataclass
class Let(Statement):
    varname: str
    expr: Expression
    
    def exec(self):
        variables[self.varname] = self.expr.eval()

class Operator(Node):
    pass

@dataclass
class InfixOperator(Operator):
    l: Expression
    r: Expression

class Plus(InfixOperator):
    def eval(self):
        return (self.l.eval()) + self.r.eval()
    
class Minus(InfixOperator):
    def eval(self):
        return self.l.eval() - self.r.eval()

class Equals(InfixOperator):
    def eval(self):
        return self.l.eval() == self.r.eval()
    
class Concat(InfixOperator):
    def eval(self):
        return str(self.l.eval()) + str(self.r.eval())

@dataclass
class Print(Statement):
    expr: Expression
    def exec(self):
        print(self.expr.eval());

@dataclass
class UnexpectedError(Exception):
    expected: str
    token: Token
    
    def __str__(self):
        return "Expected %s, got %s" % (self.expected, self.token)
        
def readString(line, pos, f):
    value = ""
    while True:
        c = f.read(1)
        if c == "\"": return StringToken(line, pos, value)
        value += c

def tokenize(filename):
    """Read a list of tokens from a file"""
    with open(filename, "r") as f:
        line = 1
        pos = 0
        token = ""
        separators = [" ", "\t", "\n", "\r"]
        while True:
            c = f.read(1)
            pos = pos + 1
            if not c: return
        
            if c in separators:
                if len(token) > 0:
                    yield Token(line, pos-len(token), token)
                if c == '\n':
                    line += 1
                    pos = 0
                token = ""
            elif c in operators:
                if len(token) > 0:
                    yield Token(line, pos-len(token), token)
                yield Token(line, pos, c)
                token = ""
            elif c == "\"":
                yield readString(line, pos, f)
                token = ""
            else:
                token += c
                #print("line %d pos %d token=%s" % (line, pos, token))
            
            
#    return [
#        "PRINT", "Start of program",
#        "IF", "1", "=", "1", "THEN", 
#            "PRINT", "  " , "&", "1", "+", "2", "+", "2", 
#            "PRINT", "  " , "&", "3", "+", "4", "+", "5", 
#            "IF", "1", "=", "1", "THEN", 
#                "PRINT", "    One equals One",
#            "ENDIF",
#        "ELSE", 
#            "PRINT", "Whu?", 
#        "ENDIF",
#        "PRINT", "End of program"
#    ]

def convToken(token):
    if isinstance(token, StringToken):
        return String(token.value)
    elif token.value.isnumeric():
        return Number(token.value)
    else:
        return Variable(token.value)

def parseExpression(it):
    token = it.__next__()

        
    l = convToken(token)
        
    if it.peek not in operators:
        return l # This was just a value

    # We are parsing an infix expression, get the operator
    op = it.__next__()
    
    # Get the rvalue (which may itself be an expression). All expressions
    # are evaluated strictly right-to-left
    r = parseExpression(it)

    # Now create the operation object
    if op == "=":
        return Equals(l, r)
    elif op == "+":
        return Plus(l, r)
    elif op == "-":
        return Minus(l, r)
    elif op == "&":
        return Concat(l, r)
    else:
        raise Exception("Unknown operation %s" % (op))

def parseStatement(it):
    token = it.__next__()
    if   token == "IF":     return parseIf(it)
    elif token == "PRINT":  return parsePrint(it)
    elif token == "FOR":    return parseFor(it)
    elif token == "LET":    return parseLet(it)
    
    # Special case of let statement without let
    node = convToken(token)
    if isinstance(node, Variable) and it.peek == "=":
        it.__next__() # Skip over the equals sign
        return Let(node.name, parseExpression(it))
    
    raise UnexpectedError("statement", token)
    
def parseFor(it):
    varname = it.__next__().value
    
    eq = it.__next__()
    if eq != "=":
        raise UnexpectedError("=", eq)

    initialValue = parseExpression(it)
    
    to = it.__next__()
    if to != "TO":
        raise UnexpectedError("TO", to)
    
    finalValue = parseExpression(it)
    
    body = []
    while it.peek != "END":
        body.append(parseStatement(it))
    body = Statements(body)
    
    end = it.__next__()
    if end != "END":
        raise UnexpectedError("END", end)
    
    return For(varname, initialValue, finalValue, body)
    
def parsePrint(it):
    return Print(parseExpression(it))

def parseIf(it):
    expr = parseExpression(it)

    if it.peek != "THEN":
        raise UnexpectedError("THEN", it.__next__())
    it.__next__()

    thenDo = []
    while it.peek != "ELSE" and it.peek != "END":
        thenDo.append(parseStatement(it))
    thenDo = Statements(thenDo)

    elseDo = []
    if it.peek == "ELSE":
        it.__next__()
        while it.peek != "END":
            elseDo.append(parseStatement(it))
    elseDo = Statements(elseDo)
    
    if it.peek != "END":
        raise UnexpectedError("END", it.__next__())
    it.__next__()
    
    return If(expr, thenDo, elseDo)

def parseLet(it):
    varname = it.__next__().value
    
    # Skip the equals sign
    eq = it.__next__()
    if eq != "=":
        raise UnexpectedError("=", eq)
    
    expr = parseExpression(it)
    
    return Let(varname, expr)

def parse(tokens):
    """Turn a list of tokens into an AST"""

    # A program is an ordered list of statements
    program = []

    it = Lookahead(tokens)

    while True:
        try:
            stmt = parseStatement(it)
            program.append(stmt)
        except StopIteration:
            break
        except UnexpectedError:
            raise
        except Exception:
            print(program)
            raise
        
    return program

def main(argc, argv):
    tokens = tokenize(argv[1])
    if argc == 3 and argv[2] == "--debug":
        for t in tokens:
            print("[%s]" % t)
            
    try:
        program = parse(tokens)
        for stmt in program:
            stmt.exec()
    except UnexpectedError as e:
        print(e)
        
if __name__ == '__main__':
    main(len(sys.argv), sys.argv)
    
    
    
