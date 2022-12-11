from parser.structures.syntax.statements.Statement import Statement
from parser.structures.running.EvaluationVariables import EvaluationVariables
from parser.structures.syntax.expressions.Expression import Expression
from parser.structures.syntax.expressions.base_literals.Variable import Variable


class LetStatement(Statement):
    def __init__(self, variable: Variable, expr: Expression):
        self.varname = variable.name
        self.value = expr
        
    def run(self, vars: EvaluationVariables):
        vars.set(self.varname, self.value.evaluate(vars))