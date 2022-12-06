from parser.structures.running.EvaluationResult import EvaluationResult, EvaluationResultType
from parser.structures.running.EvaluationVariables import EvaluationVariables
from parser.structures.syntax.expressions.Expression import Expression


class Division(Expression):
    def __init__(self, left: Expression, right: Expression) -> None:
        self.left = left
        self.right = right

    def evaluate(self, vars: EvaluationVariables) -> EvaluationResult:
        left_res = self.left.evaluate(vars)
        right_res = self.right.evaluate(vars)
        
        if right_res.type == EvaluationResultType.NUMBER and right_res.value == 0:
            return EvaluationResult(EvaluationResultType.UNDEFINED_OUT_OF_DOMAIN, None)

        if left_res.type == EvaluationResultType.UNDEFINED_OUT_OF_DOMAIN or right_res.type == EvaluationResultType.UNDEFINED_OUT_OF_DOMAIN:
            return EvaluationResult(EvaluationResultType.UNDEFINED_OUT_OF_DOMAIN, None)

        if(left_res.type == EvaluationResultType.NUMBER and
            right_res == EvaluationResultType.NUMBER):
            return EvaluationResult(
                EvaluationResultType.NUMBER, left_res.value / right_res.value
            )
        
        raise Exception(f'Could not divide {left_res.type} and {right_res.type}')