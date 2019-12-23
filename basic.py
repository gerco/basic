#!/usr/bin/python

'''
Documentation, License etc.

@package basic
'''

import sys
import os
from dataclasses import dataclass
from typing import List

operators = ["+", "-", "/", "*", "<", ">", "=", "&"]
program   = []
pc        = 0
newpc     = 0
variables = {}
labels    = {}

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
        return "%s at line %d, pos %d" % (repr(self.value), self.line, self.pos)

@dataclass
class StringToken(Token):
    def __eq__(self, other):
        return False;
    
    def ___str__(self):
        return "String(%s)" % self.value
    
@dataclass
class NewLineToken(Token):
    pass

class Node:
    pass

class Statement(Node):
    pass

class Expression(Node):
    pass

@dataclass
class Number(Expression):
    value: float
    def __init__(self, value):
        self.value = float(value)
    def eval(self):
        return self.value;
    def __str__(self):
        return str(self.value)
    
@dataclass
class String(Expression):
    value: str
    def eval(self):
        return self.value
    def __str__(self):
        return "\"%s\"" % self.value    

@dataclass
class Variable(Expression):
    name: str
    def eval(self):
        return variables[self.name]
    def __str__(self):
        return self.name
    
@dataclass
class Label(Node):
    name: str

@dataclass
class Let(Statement):
    varname: str
    expr: Expression
    
    def exec(self):
        variables[self.varname] = self.expr.eval()
        
    def __str__(self):
        return "LET %s = %s" % (self.varname, self.expr)

class Goto(Statement):
    label: str
    pc: str
    
    def __init__(self, label=None, pc=None):
        if label != None: self.label = label
        if pc    != None: self.pc    = pc
        if label is None and pc is None:
            raise Exception("Invalid Goto: no destination")
    
    def exec(self):
        global newpc

        if not(hasattr(self, 'pc')):
            try:
                self.pc = labels[self.label]
            except KeyError:
                raise Exception("Label %s not found" % self.label)
                
        newpc = self.pc
        
    def __str__(self):
        return "GOTO %s" % (self.label if hasattr(self, 'label') else self.pc)
        
@dataclass
class If(Statement):
    expr: Expression()
    ifTrue: Goto
    ifFalse: Goto
    
    def exec(self):
        if self.expr.eval() == True:
            if self.ifTrue != None:
                self.ifTrue.exec()
        else:
            if self.ifFalse != None:
                self.ifFalse.exec()
                
    def __str__(self):
        return "IF %s %s %s" % (self.expr, 
                                "THEN %s" % self.ifTrue  if self.ifTrue  != None else "", 
                                "ELSE %s" % self.ifFalse if self.ifFalse != None else "")
                
class Nop(Statement):
    def exec(self):
        pass
    def __str__(self):
        return "NOP";

class Operator(Node):
    pass

@dataclass
class InfixOperator(Operator):
    l: Expression
    r: Expression
    def __str__(self):
        return "%s %s %s" % (self.l, self.o, self.r)

class Plus(InfixOperator):
    o = "+"
    def eval(self):
        return (self.l.eval()) + self.r.eval()
    
class Minus(InfixOperator):
    o = "-"
    def eval(self):
        return self.l.eval() - self.r.eval()

class Equals(InfixOperator):
    o = "="
    def eval(self):
        return self.l.eval() == self.r.eval()

class GreaterThan(InfixOperator):
    o = ">"
    def eval(self):
        return self.l.eval() > self.r.eval()
    
class LessThan(InfixOperator):
    o = "<"
    def eval(self):
        return self.l.eval() < self.r.eval()
    
class Concat(InfixOperator):
    o = "&"
    def eval(self):
        return str(self.l.eval()) + str(self.r.eval())

@dataclass
class Print(Statement):
    expr: Expression
    def exec(self):
        print(self.expr.eval());
    def __str__(self):
        return "PRINT %s" % self.expr

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
        if c == "\"": return (StringToken(line, pos, value), len(value)+1)
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
                    yield NewLineToken(line, pos, c)
                    line += 1
                    pos = 0
                token = ""
            elif c in operators:
                if len(token) > 0:
                    yield Token(line, pos-len(token), token)
                yield Token(line, pos, c)
                token = ""
            elif c == "\"":
                token, length = readString(line, pos, f)
                pos += length
                yield token
                token = ""
            else:
                token += c
                #print("line %d pos %d token=%s" % (line, pos, token))

def convToken(token):
    if isinstance(token, StringToken):
        return String(token.value)
    elif token.value.isnumeric():
        return Number(token.value)
    elif token.value.endswith(":"):
        return Label(token.value[:-1])
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

    # Now create the operator object
    if   op == "=": return Equals(l, r)
    elif op == "+": return Plus(l, r)
    elif op == "-": return Minus(l, r)
    elif op == "&": return Concat(l, r)
    elif op == "<": return LessThan(l, r)
    elif op == ">": return GreaterThan(l, r)
    else: raise Exception("Unknown operator %s" % (op))

def parseStatement(it, program):
    token = it.__next__()
    if   token == "IF":     parseIf(   it, program)
    elif token == "PRINT":  parsePrint(it, program)
    elif token == "FOR":    parseFor(  it, program)
    elif token == "LET":    parseLet(  it, program)
    elif token == "REM":    parseRem(  it)
    elif token == "GOTO":   program.append(Goto(label=it.__next__().value))
    elif isinstance(token, NewLineToken): pass
    else:
        node = convToken(token)
        if isinstance(node, Variable) and it.peek == "=":
            # Special case of let statement without let
            it.__next__() # Skip over the equals sign
            program.append(Let(node.name, parseExpression(it)))
        elif isinstance(node, Label):
            # Label points to the next statement
            labels[node.name] = len(program)
        else:
            raise UnexpectedError("statement", token)

def parseRem(it):
    while not(isinstance(it.peek, NewLineToken)):
        next(it)

def parseFor(it, program):
    varname = it.__next__().value
    
    eq = it.__next__()
    if eq != "=":
        raise UnexpectedError("=", eq)

    initialValue = parseExpression(it)
    program.append(Let(varname, initialValue))
    
    to = it.__next__()
    if to != "TO":
        raise UnexpectedError("TO", to)
    
    finalValue = parseExpression(it)
    
    startOfLoopPC = len(program)
    
    while it.peek != "NEXT":
        parseStatement(it, program)

    program.append(Let(varname, Plus(Variable(varname), Number(1))));
    program.append(If(LessThan(Variable(varname), finalValue), Goto(pc=startOfLoopPC), None))
    
    end = it.__next__()
    if end != "NEXT":
        raise UnexpectedError("NEXT", end)

    # The variable name is allowed to follow NEXT
    if it.peek == varname:
        it.__next__()
    
def parsePrint(it, program):
    program.append(Print(parseExpression(it)))

def parseIf(it, program):
    expr = parseExpression(it)

    # Read and skip the THEN keyword
    if it.peek != "THEN":
        raise UnexpectedError("THEN", it.__next__())
    it.__next__()
    
    # Reserve some space for the If statement
    ifPC = len(program)
    program.append(None)

    # Parse and generate code for the THEN block
    thenPC = len(program)
    while it.peek != "ELSE" and it.peek != "END":
        parseStatement(it, program)
        
    # At the end of the THEN code, we have to jump 
    # over the ELSE block. We need another GOTO here
    # but we don't know the address yet
    jmpOverElsePC = None

    # Generate code for the ELSE block, if any
    elsePC = None
    if it.peek == "ELSE":
        jmpOverElsePC = len(program)
        program.append(None)
        elsePC = len(program)
        it.__next__()
        while it.peek != "END":
            parseStatement(it, program)
    
    # Read and skip end END keyword
    if it.peek != "END":
        raise UnexpectedError("END", it.__next__())
    it.__next__()
    
    program[ifPC]=If(expr, Goto(pc=thenPC), Goto(pc=elsePC) if elsePC != None else Goto(pc=len(program)))
    if jmpOverElsePC != None:
        program[jmpOverElsePC] = Goto(pc=len(program))

def parseLet(it, program):
    varname = it.__next__().value
    
    # Skip the equals sign
    eq = it.__next__()
    if eq != "=":
        raise UnexpectedError("=", eq)
    
    expr = parseExpression(it)
    
    program.append(Let(varname, expr))

def parse(tokens):
    """Turn a list of tokens into an ASL"""

    # A program is an ordered list of statements
    program = []

    it = Lookahead(tokens)

    while True:
        try:
            parseStatement(it, program)
        except StopIteration:
            break
        except UnexpectedError:
            raise
        except Exception:
            print(program)
            raise
        
    return program

def main(argc, argv):
    global program, pc, newpc
    
    tokens = tokenize(argv[1])
    if argc == 3 and argv[2] == "--debug":
        for t in tokens:
            print("[%s]" % t)
            
    program = parse(tokens)
    if argc == 3 and argv[2] == "--asl":
        for i, stmt in enumerate(program):
            print("%3d   %s" % (i, stmt))
        print(labels)
        return
    
    pc = 0
    while pc < len(program):
        newpc = pc + 1
        program[pc].exec()
        pc = newpc
        
if __name__ == '__main__':
    main(len(sys.argv), sys.argv)
    
    
    
