import copy
from enum import Enum

from brewparse import parse_program
from env_v2 import EnvironmentManager
from intbase import InterpreterBase, ErrorType
from type_valuev2 import Type, Value, create_value, get_printable

class ExecStatus(Enum):
    CONTINUE = 1
    RETURN = 2


# Main interpreter class
class Interpreter(InterpreterBase):
    # constants
    NIL_VALUE = create_value(InterpreterBase.NIL_DEF)
    TRUE_VALUE = create_value(InterpreterBase.TRUE_DEF)
    BIN_OPS = {"+", "-", "*", "/", "==", "!=", ">", ">=", "<", "<=", "||", "&&"}

    # methods
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)
        self.trace_output = trace_output
        self.__setup_ops()

    # run a program that's provided in a string
    # usese the provided Parser found in brewparse.py to parse the program
    # into an abstract syntax tree (ast)
    def run(self, program):
        ast = parse_program(program)
        self.__set_up_function_table(ast)
        self.env = EnvironmentManager()
        self.save_env = None
        main_func = self.__get_func_by_name("main", 0)
        self.__run_statements(main_func.get("statements"))

    def __set_up_function_table(self, ast):
        self.func_name_to_ast = {}
        for func_def in ast.get("functions"):
            func_name = func_def.get("name")
            num_params = len(func_def.get("args"))
            if func_name not in self.func_name_to_ast:
                self.func_name_to_ast[func_name] = {}
            self.func_name_to_ast[func_name][num_params] = func_def

    def __get_func_by_name(self, name, num_params):
        # check to see if name is set as lambda in env
        if name not in self.func_name_to_ast:
            func = self.env.get(name)
            if func == None:
                super().error(ErrorType.NAME_ERROR, f"Function {func} not found")
            if func.type() == Type.FUNC:
                if len(func.value().get("args")) != num_params:
                    super().error(ErrorType.TYPE_ERROR, f"Invalid number of parameters for {name}")
                return func.value()
            if func.type() == Type.LAMBDA:
                if len((func.value()[0]).get("args")) != num_params:
                    super().error(ErrorType.TYPE_ERROR, f"Invalid number of parameters for {name}")
                return func
            super().error(ErrorType.TYPE_ERROR, f"Variable {name} is not a function")
        candidate_funcs = self.func_name_to_ast[name]
        # check if overloaded function
        if num_params == -1:
            if len(candidate_funcs) == 1:
                num_params = list(candidate_funcs.keys())[0]
                return candidate_funcs[num_params]
            super().error(
                ErrorType.NAME_ERROR,
                f"Can't assign {name} to variable, overloaded function"
            )
        if num_params not in candidate_funcs:
            super().error(
                ErrorType.NAME_ERROR,
                f"Function {name} taking {num_params} params not found",
            )
        return candidate_funcs[num_params]

    def __run_statements(self, statements):
        self.env.push()
        for statement in statements:
            # print(statement)
            if self.trace_output:
                print(statement)
            status = ExecStatus.CONTINUE
            if statement.elem_type == InterpreterBase.FCALL_DEF:
                self.__call_func(statement)
            elif statement.elem_type == "=":
                self.__assign(statement)
            elif statement.elem_type == InterpreterBase.RETURN_DEF:
                status, return_val = self.__do_return(statement)
            elif statement.elem_type == Interpreter.IF_DEF:
                status, return_val = self.__do_if(statement)
            elif statement.elem_type == Interpreter.WHILE_DEF:
                status, return_val = self.__do_while(statement)

            if status == ExecStatus.RETURN:
                self.env.pop()
                return (status, return_val)

        self.env.pop()
        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)

    def __call_func(self, call_node):
        func_name = call_node.get("name")
        if func_name == "print":
            return self.__call_print(call_node)
        if func_name == "inputi":
            return self.__call_input(call_node)
        if func_name == "inputs":
            return self.__call_input(call_node)

        actual_args = call_node.get("args")
        func_ast = self.__get_func_by_name(func_name, len(actual_args))
        lambda_ast = func_ast
        if isinstance(func_ast, Value):
            if func_ast.type()== Type.LAMBDA:
                formal_args = (func_ast.value()[0]).get("args")
            func_ast = func_ast.value()[0]
        else:
            formal_args = func_ast.get("args")
        if len(actual_args) != len(formal_args):
            super().error(
                ErrorType.NAME_ERROR,
                f"Function {func_ast.get('name')} with {len(actual_args)} args not found",
            )
        self.env.push()
        if isinstance(lambda_ast, Value) and lambda_ast.type()== Type.LAMBDA:
                self.save_env = self.env
                self.env = (lambda_ast.value()[1])
                # print(self.env.environment)
        for formal_ast, actual_ast in zip(formal_args, actual_args):
            arg_name = formal_ast.get("name")
            result = copy.deepcopy(self.__eval_expr(actual_ast))
            if formal_ast.elem_type == "refarg" and actual_ast.elem_type == 'var':
                self.env.create(arg_name, [Value("refvar", result), actual_ast.get('name')])
            else:
                self.env.create(arg_name, result)
            
        _, return_val = self.__run_statements(func_ast.get("statements"))
        if isinstance(lambda_ast, Value) and lambda_ast.type()== Type.LAMBDA:
                ## save the prior environment before lambda exits
                self.env = self.save_env
                # self.save_env = None
        self.env.pop()
        return return_val

    def __call_print(self, call_ast):
        output = ""
        for arg in call_ast.get("args"):
            # print(self.env.environment)
            result = self.__eval_expr(arg)  # result is a Value object
            output = output + get_printable(result)
        super().output(output)
        return Interpreter.NIL_VALUE

    def __call_input(self, call_ast):
        args = call_ast.get("args")
        if args is not None and len(args) == 1:
            result = self.__eval_expr(args[0])
            super().output(get_printable(result))
        elif args is not None and len(args) > 1:
            super().error(
                ErrorType.NAME_ERROR, "No inputi() function that takes > 1 parameter"
            )
        inp = super().get_input()
        if call_ast.get("name") == "inputi":
            return Value(Type.INT, int(inp))
        if call_ast.get("name") == "inputs":
            return Value(Type.STRING, inp)

    def __assign(self, assign_ast):
        var_name = assign_ast.get("name")
        val = self.env.get(var_name)
        # print("assign expr", assign_ast.get("expression"))
        value_obj = self.__eval_expr(assign_ast.get("expression"))
        # val is none when it doesn't exist in our current env,
        # and it needs to be set in current env
        if val is not None:
            # if refarg, .get will return a list [Value, refvar name]
            if isinstance(val, list):
                if val[0].type() == "refvar":
                    print(val)
                    self.env.set_ref(val[1], value_obj, self.save_env)
                       
            else:
                self.env.set(var_name, value_obj)

        else:
            self.env.set(var_name, value_obj)

    def __eval_expr(self, expr_ast):
        if isinstance(expr_ast, list):
            # if expr_ast.type() 
            var_name = expr_ast[1]
            value = self.env.get_ref(var_name, self.save_env, 1)
            # print("from eval: ", value)
            if isinstance(value, list):
                print(value)
                return self.__eval_expr(value)
            if value == None:
                super().error(ErrorType.NAME_ERROR, f"Variable {var_name} not found")
            return value
        if expr_ast.elem_type == InterpreterBase.NIL_DEF:
            return Interpreter.NIL_VALUE
        if expr_ast.elem_type == InterpreterBase.INT_DEF:
            return Value(Type.INT, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.STRING_DEF:
            return Value(Type.STRING, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.BOOL_DEF:
            return Value(Type.BOOL, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.VAR_DEF:
            var_name = expr_ast.get("name")
            val = self.env.get(var_name)
            # will return a list if refarg
            if isinstance(val, list):
                return self.__eval_expr(val)
            if val is None:
                val = self.__get_func_by_name(var_name, -1)
                if val.elem_type != InterpreterBase.FUNC_DEF and val.elem_type != InterpreterBase.LAMBDA_DEF:
                    super().error(ErrorType.NAME_ERROR, f"Variable {var_name} not found")
                if val.elem_type == InterpreterBase.FUNC_DEF:
                    return Value(Type.FUNC, val)
                if val.elem_type == InterpreterBase.LAMBDA_DEF:
                    return Value(Type.LAMBDA, val)
            return val
        if expr_ast.elem_type == InterpreterBase.FCALL_DEF:
            return self.__call_func(expr_ast)
        if expr_ast.elem_type in Interpreter.BIN_OPS:
            return self.__eval_op(expr_ast)
        if expr_ast.elem_type == Interpreter.NEG_DEF:
            return self.__eval_unary(expr_ast, Type.INT, lambda x: -1 * x)
        if expr_ast.elem_type == Interpreter.NOT_DEF:
            return self.__eval_unary(expr_ast, Type.BOOL, lambda x: not x)
        if expr_ast.elem_type == InterpreterBase.LAMBDA_DEF:
            return self.__handle_lambdas(expr_ast)
    
    def __handle_lambdas(self, lambda_ast):
        lambEnvironment = copy.deepcopy(self.env)
        # print(lambEnvironment.environment)
        return Value(Type.LAMBDA, [lambda_ast, lambEnvironment])
    

    def __eval_op(self, arith_ast):
        left_value_obj = self.__eval_expr(arith_ast.get("op1"))
        right_value_obj = self.__eval_expr(arith_ast.get("op2"))
        if not self.__compatible_types(
            arith_ast.elem_type, left_value_obj, right_value_obj
        ):
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible types for {arith_ast.elem_type} operation",
            )
        
        if right_value_obj.type() == Type.NIL:
            op_type = right_value_obj.type()
        else:
            op_type = left_value_obj.type()

        if arith_ast.elem_type not in self.op_to_lambda[op_type]:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible operator {arith_ast.elem_type} for type {op_type}",
            )
        f = self.op_to_lambda[op_type][arith_ast.elem_type]
        return f(left_value_obj, right_value_obj)

    def __compatible_types(self, oper, obj1, obj2):
        # DOCUMENT: allow comparisons ==/!= of anything against anything
        if oper in ["==", "!="]:
            return True
        # Use of any comparison operator other than == and != on a 
        # variable holding a function/closure must result in an error of ErrorType.TYPE_ERROR.
        if oper not in ["==", "!="]:
            if obj1.type() == Type.LAMBDA or obj2 == Type.LAMBDA or obj1.type() == Type.FUNC or obj2 == Type.FUNC:
                return False
        if oper in ["||", "&&"]:
            if (obj1.type() == Type.BOOL and obj2.type() == Type.INT) or (obj1.type() == Type.INT and obj2.type() == Type.BOOL):
                return True
        if oper in ["+", "-", "*", "/"]:
            if (obj1.type() == Type.BOOL and obj2.type() == Type.INT) or (obj1.type() == Type.INT and obj2.type() == Type.BOOL):
                return True
        return obj1.type() == obj2.type()

    def __eval_unary(self, arith_ast, type, function):
        value_obj = self.__eval_expr(arith_ast.get("op1"))
        if value_obj.type() == Type.INT:
            return Value(Type.BOOL, function(value_obj.value()))
        if value_obj.type() != type:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible type for {arith_ast.elem_type} operation",
            )
        return Value(type, function(value_obj.value()))

    def __setup_ops(self):
        self.op_to_lambda = {}
        # set up operations on integers
        self.op_to_lambda[Type.INT] = {}
        self.op_to_lambda[Type.INT]["+"] = lambda x, y: Value(
            x.type(), int(x.value()) + int(y.value())
        )
        self.op_to_lambda[Type.INT]["-"] = lambda x, y: Value(
            x.type(), int(x.value()) - int(y.value())
        )
        self.op_to_lambda[Type.INT]["*"] = lambda x, y: Value(
            x.type(), int(x.value()) * int(y.value())
        )
        self.op_to_lambda[Type.INT]["/"] = lambda x, y: Value(
            x.type(), int(x.value()) // int(y.value())
        )
        self.op_to_lambda[Type.INT]["=="] = lambda x, y: Value(
            Type.BOOL, (x.type() == y.type() or y.type() == Type.BOOL) and bool(x.value()) == bool(y.value())
        )
        self.op_to_lambda[Type.INT]["!="] = lambda x, y: Value(
            Type.BOOL, (x.type() != y.type() and y.type() != Type.BOOL) or bool(x.value()) != bool(y.value())
        )
        self.op_to_lambda[Type.INT]["<"] = lambda x, y: Value(
            Type.BOOL, x.value() < y.value()
        )
        self.op_to_lambda[Type.INT]["<="] = lambda x, y: Value(
            Type.BOOL, x.value() <= y.value()
        )
        self.op_to_lambda[Type.INT][">"] = lambda x, y: Value(
            Type.BOOL, x.value() > y.value()
        )
        self.op_to_lambda[Type.INT][">="] = lambda x, y: Value(
            Type.BOOL, x.value() >= y.value()
        )
        self.op_to_lambda[Type.INT]["&&"] = lambda x, y: Value(
            Type.BOOL, bool(x.value() and y.value())
        )
        self.op_to_lambda[Type.INT]["||"] = lambda x, y: Value(
            Type.BOOL, bool(x.value() or y.value())
        )
        #  set up operations on strings
        self.op_to_lambda[Type.STRING] = {}
        self.op_to_lambda[Type.STRING]["+"] = lambda x, y: Value(
            x.type(), x.value() + y.value()
        )
        self.op_to_lambda[Type.STRING]["=="] = lambda x, y: Value(
            Type.BOOL, x.value() == y.value()
        )
        self.op_to_lambda[Type.STRING]["!="] = lambda x, y: Value(
            Type.BOOL, x.value() != y.value()
        )
        #  set up operations on bools
        self.op_to_lambda[Type.BOOL] = {}
        self.op_to_lambda[Type.BOOL]["&&"] = lambda x, y: Value(
            x.type(), x.value() and y.value()
        )
        self.op_to_lambda[Type.BOOL]["||"] = lambda x, y: Value(
            x.type(), x.value() or y.value()
        )
        self.op_to_lambda[Type.BOOL]["=="] = lambda x, y: Value(
            Type.BOOL, (x.type() == y.type() or y.type() == Type.INT) and bool(x.value()) == bool(y.value())
        )
        self.op_to_lambda[Type.BOOL]["!="] = lambda x, y: Value(
            Type.BOOL, (x.type() != y.type() and y.type() != Type.BOOL) or bool(x.value()) != bool(y.value())
        )
        self.op_to_lambda[Type.BOOL]["+"] = lambda x, y: Value(
            Type.INT, int(x.value()) + int(y.value())
        )
        self.op_to_lambda[Type.BOOL]["-"] = lambda x, y: Value(
            Type.INT, int(x.value()) - int(y.value())
        )
        self.op_to_lambda[Type.BOOL]["*"] = lambda x, y: Value(
            Type.INT, int(x.value()) * int(y.value())
        )
        self.op_to_lambda[Type.BOOL]["/"] = lambda x, y: Value(
            Type.INT, int(x.value()) // int(y.value())
        )
        #  set up operations on nil
        self.op_to_lambda[Type.NIL] = {}
        self.op_to_lambda[Type.NIL]["=="] = lambda x, y: Value(
            Type.BOOL, x.type() == y.type() and x.value() == y.value()
        )
        self.op_to_lambda[Type.NIL]["!="] = lambda x, y: Value(
            Type.BOOL, x.type() != y.type() or x.value() != y.value()
        )
        # set up operations on functions
        self.op_to_lambda[Type.FUNC] = {}
        self.op_to_lambda[Type.FUNC]["=="] = lambda x, y: Value(
            Type.BOOL, x.value().get("name") == y.value().get("name") and len(x.value().get("args")) == len(y.value().get("args"))
        ) if x.type() == y.type() else Value(Type.BOOL, False)
        self.op_to_lambda[Type.FUNC]["!="] = lambda x, y: Value(
            Type.BOOL, x.value().get("name") != y.value().get("name") or len(x.value().get("args")) != len(y.value().get("args"))
        ) if x.type() == y.type() else Value(Type.BOOL, True)
        # set up operation on lambdas
        self.op_to_lambda[Type.LAMBDA] = {}
        self.op_to_lambda[Type.LAMBDA]["=="] = lambda x, y: Value(
            Type.BOOL, (x.value()[0]).get("name") == (y.value()[0]).get("name") and 
            len((x.value()[0]).get("args")) == len((y.value()[0]).get("args"))
        ) if x.type() == y.type() else Value(Type.BOOL, False)
        self.op_to_lambda[Type.LAMBDA]["!="] = lambda x, y: Value(
            Type.BOOL, (x.value()[0]).get("name") != (y.value()[0]).get("name") or len((x.value()[0]).get("args")) != len((y.value()[0]).get("args"))
        ) if x.type() == y.type() else Value(Type.BOOL, True)
        # NEED TO FIX THIS ?
        # Note that a copy of a closure or function (e.g., one returned by a function, 
        # since functions return deep copies) is NOT the same as the original closure/function, 
        # so comparison using == would be false, and != would be true:

    def __do_if(self, if_ast):
        cond_ast = if_ast.get("condition")
        result = self.__eval_expr(cond_ast)
        if result.type() == Type.INT:
            result = Value(Type.BOOL, result.value())
        if result.type() != Type.BOOL:
            super().error(
                ErrorType.TYPE_ERROR,
                "Incompatible type for if condition",
            )
        if result.value():
            statements = if_ast.get("statements")
            status, return_val = self.__run_statements(statements)
            return (status, return_val)
        else:
            else_statements = if_ast.get("else_statements")
            if else_statements is not None:
                status, return_val = self.__run_statements(else_statements)
                return (status, return_val)

        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)

    def __do_while(self, while_ast):
        cond_ast = while_ast.get("condition")
        run_while = Interpreter.TRUE_VALUE
        while run_while.value():
            run_while = self.__eval_expr(cond_ast)
            if run_while.type() == Type.INT:
                run_while = Value(Type.BOOL, run_while.value())
            if run_while.type() != Type.BOOL:
                super().error(
                    ErrorType.TYPE_ERROR,
                    "Incompatible type for while condition",
                )
            if run_while.value():
                statements = while_ast.get("statements")
                status, return_val = self.__run_statements(statements)
                if status == ExecStatus.RETURN:
                    return status, return_val

        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)

    def __do_return(self, return_ast):
        expr_ast = return_ast.get("expression")
        if expr_ast is None:
            return (ExecStatus.RETURN, Interpreter.NIL_VALUE)
        value_obj = copy.deepcopy(self.__eval_expr(expr_ast))
        return (ExecStatus.RETURN, value_obj)
