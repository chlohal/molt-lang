# This is one of the most complex sub-parsers because it needs to discriminate between 4 cases:
# - Set builder notation: `f(x) = { y | y = x }` should be 'f of x is the set of all y where y is less than x'
# - Braced expressions: `f(x) = { x | g(x) }` should be 'f of x is the union of x and (g of x)'
# - Piecewise: `f(x) = { x = 2: 2, x = 3: 9 }` should be 'f of x is 2 if x is 2 and is 9 if x is 3'
# - Finite set: `f(y) = { y | y, y }` should be a set containing `y | y` and `y`.
# - (there are also unbraced expressions, but those are so easy that we don't need to care about them.)
#
# The third one is relatively easy; we need to crack `parse_condition` open 
# a little bit, but it's doable. The first two are FAR harder
# to discriminate between: the only difference is that the former uses
# conditions and the latter uses expressions.
# It's *doable*, but it's hard to understand for everyone.
#
# The even harder part is that it's literally impossible to 
# discriminate between a braced expression and a single-element finite set.
# so we have to add an optional argument to specify the context-- which structure we *actually* want that lexical form
# to yield.
# 
# The main tricky part is:
# `f(x) = { y | y = x }` should be a set
# `f(x) = { y | y = x: 2 }` should be a piecewise (albeit a WEIRD one-- here's some more explanatory parens: `f(x) = { (y | y) = x: 2 }`)
# `f(x) = { y | y }` should be a braced expression. or maybe a single-element set. wacky, huh?

from typing import List, Tuple
from molt.src.parser.parsing.parse_condition import parse_condition, parse_condition_with_left
from molt.src.parser.parsing.parse_expression import parse_expression
from molt.src.parser.parsing.parse_utils import expect
from molt.src.parser.parsing.token_stream import TokenStream
from molt.src.parser.structures.syntax.conditions.Condition import Condition
from molt.src.parser.structures.syntax.conditions.Equation import Equation
from molt.src.parser.structures.syntax.expressions.Expression import Expression
from molt.src.parser.structures.syntax.expressions.PiecewiseNotation import PiecewiseNotation
from molt.src.parser.structures.syntax.expressions.base_literals.Variable import Variable
from molt.src.parser.structures.syntax.expressions.compound_literals.FiniteSet import FiniteSet
from molt.src.parser.structures.syntax.expressions.compound_literals.InfiniteSet import InfiniteSet
from molt.src.parser.structures.syntax.expressions.set_operations.Union import Union


def parse_function_body(tokens: TokenStream) -> Expression:
    # If the first token isn't a curly bracket, then the body MUST be a plain expression. That's really easy.
    if tokens.peek().type != "curly_obracket":
        return parse_expression(tokens)
    
    # consume the curly!
    # we know it's a curly bc of the above `if` statement
    tokens.pop()
    
    # segment out this part so that set expressions can use the latter.
    return parse_function_body_after_curly(tokens)
    
def parse_function_body_after_curly(tokens: TokenStream, parse_singleton_set_as_expression = True) -> Expression:
    # consume an expression first. All 3 cases start with an expression (LEXICALLY), so that's good.
    # we might need to crack open the expression later, but uhhh yikes we can get to that when we get to it.
    first_expr = parse_expression(tokens)
    # if the next token is a close bracket, wonderful! We've parsed a bracketed expression or a singleton set
    if(tokens.peek().type == "curly_cbracket"):
        tokens.pop()
        
        if parse_singleton_set_as_expression:
            return first_expr
        else:
            return FiniteSet([first_expr])
            
    # if the next token is a comma, we're in a finite set
    if tokens.peek().type == "comma":
        return parse_rest_of_finite_set(tokens, first_expr)
    
    # make a condition with the expression. We still don't
    # know if this is `x | x = y: 2` (piecewise) 
    # or `x | x = y` (set-builder notation), so we use the whole expr.
    # We can (and will!) swap it around later.
    
    condition = parse_condition_with_left(tokens, first_expr)
    
    # ok cool cool.
    # if we find a comma or a close-bracket, it's set builder.
    # if we find a colon, it's piecewise.
    # if we find anything else, complain
    
    if tokens.peek().type == "comma" or tokens.peek().type == "curly_cbracket":
        result = parse_the_rest_of_set_builder(tokens, condition)
    elif tokens.peek().type == "colon": 
        result = parse_the_rest_of_piecewise(tokens, condition)
    else:
        raise Exception("""
            Couldn't determine whether this expression is set-builder or piecewise notation.
        """)
    
    expect(tokens, "curly_cbracket", "Couldn't find a matching close-bracket.")
    
    return result
    
def parse_rest_of_finite_set(tokens: TokenStream, first: Expression) -> Expression:
    # we get a comma as the next token. We should keep going until we find a curly end.
    
    # pop the comma, which we know by precondition to exist
    tokens.pop()
    
    expressions = [first]
    
    while tokens.peek().type != 'curly_cbracket':
        expressions.append(parse_expression(tokens))
        if tokens.peek().type == 'comma':
            tokens.pop()
    
    return FiniteSet(expressions)
    
def parse_the_rest_of_piecewise(tokens: TokenStream, cond: Condition) -> PiecewiseNotation:
    # the next token MUST (by precondition) be a colon. just get rid of it :)
    tokens.pop()
    
    branches = [(cond, parse_expression(tokens))]
    
    # ok ok. now. keep on going. it'll be a series of `condition colon expression`s, seperated by `comma`s.
    # the tricky part is the last could just be an `expression`, so you've gotta check for that
    
    while tokens.peek().type == "comma":
        tokens.pop()
        
        if tokens.peek().type == "curly_cbracket":
            raise Exception("Trailing comma in piecewise notation. There isn't a comma after the final piecewise term.")
        
        next_expr = parse_expression(tokens)
        if tokens.peek().type == "curly_cbracket":
            branches.append( (Condition.TRUE, next_expr) )
            break
        elif tokens.peek().type == "comma":
            raise Exception("The 'else' clause of piecewise notation must be the last item.")
        
        next_cond = parse_condition_with_left(tokens, next_expr)
        expect(tokens, "colon", "In piecewise notation, colons must seperate conditions from their values.")
        
        expr = parse_expression(tokens)
        
        branches.append( (next_cond, expr) )
        
    # if the next token isn't a close-curly, tell the user they might want to add a comma; this helps with 
    # things like f(x) = { x == 2: 1
    # x == 3: -x }
    # where the user forgot a comma
    
    if tokens.peek().type != "curly_cbracket":
        raise Exception("In piecewise notation, terms must be seperated by commas. You might be missing one.")
    
    return PiecewiseNotation(branches)
    
    
def parse_the_rest_of_set_builder(tokens: TokenStream, cond: Condition) -> InfiniteSet:
    # we got a condition that looks like `x | x = y`. The lhs is DEFINITELY a union, but everything else
    # has to be verified. The next token is either `}`, meaning that it's over,
    # or `,`, meaning that there are more conditions.
    
    # but first lol, crack open the condition and verify it's got a variable
    
    union: Union = cond.left
    # if it WASN'T a bracketed expression, then we *had* to have parsed a set union.
    # complain if not.
    if (type(union) != Union):
        raise (Exception("""
        Experienced an issue while parsing a set-builder expression: needed a `|`, but didn't get one. Sad!
        """))
    
    
    
    initial_variable = union.left
    
    if(type(initial_variable) != Variable):
        raise Exception(f"""
            While parsing a set-builder expression, the initial bound variable was... not a variable. That's a problem.
            Set-builder notation should look like this: {{ x | x > 2}}. Instead of a variable, we found a {type(initial_variable)}.
        """)
        
    cond.left = union.right
    
    set_conditions = {cond}
    
    while tokens.peek().type == "comma":
        # pop the comma before parsing a condition!
        tokens.pop()
        set_conditions.add(parse_condition(tokens))
    
    return InfiniteSet(initial_variable, set_conditions)