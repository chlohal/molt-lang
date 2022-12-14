import sys
from molt.src.parser.structures.syntax.statements.Statement import Statement
from molt.src.parser.structures.running.EvaluationResult import EvaluationResultType
from molt.src.parser.structures.running.EvaluationVariables import EvaluationVariables
from molt.src.parser.structures.syntax.expressions.Expression import Expression


class EvalStatement(Statement):
    def __init__(self, expr: Expression):
        self.expression = expr
    
    def run(self, vars: EvaluationVariables):
        val = self.expression.evaluate(vars)
        
        if "--explain" in sys.argv:
            print(f"{val}  # {self.expression}")
        else:
            print(val)