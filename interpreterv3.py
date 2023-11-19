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
        print("CAND FUNC", name)
        if name not in self.func_name_to_ast:
            candidate_func = self.env.get(name)
            #check to see if a variable has been assigned to a func
            # print(self.env.temp_environment)
            if candidate_func is None:
                # print(candidate_func)
                super().error(ErrorType.NAME_ERROR, f"Function {name} not found")
            if candidate_func.type() == Type.REFARG:
                save_this = candidate_func
                candidate_func = self.env.get_ref(name)
                if candidate_func is None:
                    if save_this.value() in self.func_name_to_ast:
                        return self.__get_func_by_name(save_this.value(), num_params)
                        
            if candidate_func.type() == Type.FUNC:
                if num_params != len(candidate_func.value().get('args')):
                    super().error(ErrorType.TYPE_ERROR, "Invalid # of args to lambda")
                return candidate_func.value()
            if candidate_func.type() == Type.LAMBDA:
                # print(candidate_func)
                lambda_ast = self.env.get_lamb_ast(candidate_func.value())
                if num_params != len(lambda_ast.get('args')):
                    super().error(ErrorType.TYPE_ERROR, "Invalid # of args to lambda")
                return candidate_func
                
            super().error(ErrorType.TYPE_ERROR, f"Variable {name} is not a function")
        candidate_funcs = self.func_name_to_ast[name]
        if num_params not in candidate_funcs:
            super().error(
                ErrorType.NAME_ERROR,
                f"Function {name} taking {num_params} params not found",
            )
        return candidate_funcs[num_params]

    def __run_statements(self, statements):
        self.env.push()
        print()
        for statement in statements:
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

        lambda_ast = None
        actual_args = call_node.get("args")
        func_ast = self.__get_func_by_name(func_name, len(actual_args))
        # lambda functions will be a value, due to __get_func_by_name
        # this is how we know to set the environment and get the lambda_ast
        # print("CALL FUNC ENV")
        # print(self.env.environment)
        # print(self.env.temp_environment)
        if isinstance(func_ast, Value):
            self.env.set_lamb_env(func_ast.value())
            lambda_ast = func_ast
            func_ast = self.env.get_lamb_ast(func_ast.value())
        formal_args = func_ast.get("args")
        if len(actual_args) != len(formal_args):
            super().error(
                ErrorType.NAME_ERROR,
                f"Function {func_ast.get('name')} with {len(actual_args)} args not found",
            )
        self.env.push()
        for formal_ast, actual_ast in zip(formal_args, actual_args):
            arg_name = formal_ast.get("name")
            # If it's a reference arg and the result is a var:
            if formal_ast.elem_type == 'refarg' and actual_ast.elem_type == InterpreterBase.VAR_DEF:
                # self.env.check_and_set(actual_ast.get('name'), arg_name)
                self.env.create(arg_name, Value(Type.REFARG, actual_ast.get('name')))
                print("CALL FUNC ENV")
                print(self.env.environment)
                print(self.env.temp_environment)
            else:
                result = copy.deepcopy(self.__eval_expr(actual_ast))
                if result.type() == Type.LAMBDA:
                    result = self.env.create_deep_copy_lamb(result.value())
                    result = Value(Type.LAMBDA, result)
                self.env.create(arg_name, result)
        _, return_val = self.__run_statements(func_ast.get("statements"))
        self.env.pop()
        if (lambda_ast):
            self.env.set_main_env()

        return return_val

    def __call_print(self, call_ast):
        output = ""
        for arg in call_ast.get("args"):
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
        value_obj = self.__eval_expr(assign_ast.get("expression"), var_name)
        # Check the type of variable to see if it's refarg
        # if .get(var_name) is None, set it 
        var_val = self.env.get(var_name)
        if var_val is None:
            self.env.set(var_name, value_obj)
        else:
            # print("CALL ASSIGN HERE")
            # print(value_obj)
            # print(var_val)
            # print(var_name)
            if var_val.type() != Type.REFARG:
                self.env.set(var_name, value_obj)
            else:
                self.env.set_ref(var_name, value_obj)

    def __eval_expr(self, expr_ast, ref_name = None):
        print("\nhere expr")
        print(expr_ast)
        if expr_ast.elem_type == InterpreterBase.NIL_DEF:
            # print("getting as nil")
            return Interpreter.NIL_VALUE
        if expr_ast.elem_type == InterpreterBase.INT_DEF:
            return Value(Type.INT, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.STRING_DEF:
            # print("getting as str")
            return Value(Type.STRING, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.BOOL_DEF:
            return Value(Type.BOOL, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.VAR_DEF:
            var_name = expr_ast.get('name')
            val = self.env.get(var_name)
            print("FROM EVAL EXPR", val)
            if val is None:
                #check if the passed variable is a function
                val = self.__handle_function_assignment(var_name)
                if val is None:
                    if self.env.check_for_ref(var_name):
                        val = self.env.get(self.env.check_for_ref(var_name))
                    else:
                        super().error(ErrorType.NAME_ERROR, f"Variable {var_name} not found")
            if val.type() == Type.REFARG:
                print(val.value())
                val = self.env.get_ref(val.value())
            

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
            return self.__handle_lambda_assignment(expr_ast, ref_name)


    
    def __handle_function_assignment(self, func_name):
        # check to see if the func_name is a function
        if func_name not in self.func_name_to_ast:
            return None
        possible_functions = self.func_name_to_ast[func_name]
        # Check to make sure assigned function is not overloaded
        if len(possible_functions) == 1:
            return Value(Type.FUNC, list(possible_functions.values())[0])
        else:
            super().error(ErrorType.NAME_ERROR, f"Can't assign {func_name} to variable, overloaded function")
            

    def __handle_lambda_assignment(self, lambda_ast, var_name):
        # NOTE may cause issues as the lambda_env does not hold a variable holding the lambda val
        env_index = self.env.push_lambda_env(lambda_ast)
        lamb_value = Value(Type.LAMBDA, env_index)
        if self.env.get(var_name) is not None:
            if self.env.get(var_name).type() != Type.REFARG:
                self.env.create(var_name, lamb_value)
        return lamb_value

    def __eval_op(self, arith_ast):
        left_value_obj = self.__eval_expr(arith_ast.get("op1"))
        right_value_obj = self.__eval_expr(arith_ast.get("op2"))
        print("left and right")
        print(left_value_obj)
        print(right_value_obj)
        if not self.__compatible_types(
            arith_ast.elem_type, left_value_obj, right_value_obj
        ):
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible types for {arith_ast.elem_type} operation",
            )

        obj_type = left_value_obj.type()
        # If Type.INT is compared with Type.BOOL, we use the lambda self.op_to_lambda[Type.BOOL]
        # This way int comparisons still work
        if left_value_obj.type() == Type.INT and right_value_obj.type() == Type.BOOL:
            if arith_ast.elem_type in ["==", "!=", "||", "&&"]:
                obj_type = right_value_obj.type()

        if arith_ast.elem_type not in self.op_to_lambda[obj_type]:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible operator {arith_ast.elem_type} for type {obj_type}",
            )
        f = self.op_to_lambda[obj_type][arith_ast.elem_type]
        # print("here eval")
        # print(arith_ast)
        # print("evaluating " + str(left_value_obj.type()) + " " + str(arith_ast.elem_type))
        # print("obj left: " + str(left_value_obj.value()))
        return f(left_value_obj, right_value_obj)

    def __compatible_types(self, oper, obj1, obj2):
        # DOCUMENT: allow comparisons ==/!= of anything against anything
        # print(obj1)
        # print(obj2)
        if oper in ["==", "!="]:
            return True
        if oper not in ["==", "!="]:
            if obj1.type() in [Type.LAMBDA, Type.FUNC] or obj2.type() in [Type.LAMBDA, Type.FUNC]:
                return False
        if oper in Interpreter.BIN_OPS:
            if obj1.type() in [Type.BOOL, Type.INT] and obj2.type() in [Type.BOOL, Type.INT]:
                return True
        return obj1.type() == obj2.type()

    def __eval_unary(self, arith_ast, type, function):
        value_obj = self.__eval_expr(arith_ast.get("op1"))
        if value_obj.type() not in [Type.BOOL, Type.INT]:
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
            Type.BOOL, (x.type() == y.type()) and int(x.value()) == int(y.value())
        )
        self.op_to_lambda[Type.INT]["!="] = lambda x, y: Value(
            Type.BOOL, (x.type() != y.type()) or int(x.value()) != int(y.value())
        )
        self.op_to_lambda[Type.INT]["<"] = lambda x, y: Value(
            Type.BOOL, int(x.value()) < int(y.value())
        )
        self.op_to_lambda[Type.INT]["<="] = lambda x, y: Value(
            Type.BOOL, int(x.value()) <= int(y.value())
        )
        self.op_to_lambda[Type.INT][">"] = lambda x, y: Value(
            Type.BOOL, int(x.value()) > int(y.value())
        )
        self.op_to_lambda[Type.INT][">="] = lambda x, y: Value(
            Type.BOOL, int(x.value()) >= int(y.value())
        )
        self.op_to_lambda[Type.INT]["&&"] = lambda x, y: Value(
            Type.BOOL, bool(x.value() and y.value())
        )
        self.op_to_lambda[Type.INT]["||"] = lambda x, y: Value(
            Type.BOOL, bool(x.value() or y.value())
        )
        self.op_to_lambda[Type.INT]["!"] = lambda x, y: Value(
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
            x.type(), bool(x.value()) and bool(y.value())
        )
        self.op_to_lambda[Type.BOOL]["||"] = lambda x, y: Value(
            x.type(), bool(x.value()) or bool(y.value())
        )
        self.op_to_lambda[Type.BOOL]["=="] = lambda x, y: Value(
            Type.BOOL, bool(x.value()) == bool(y.value())
        )
        self.op_to_lambda[Type.BOOL]["!="] = lambda x, y: Value(
            Type.BOOL, bool(x.value()) != bool(y.value())
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
        self.op_to_lambda[Type.BOOL][">"] = lambda x, y: Value(
            Type.BOOL, bool(int(x.value()) > int(y.value()))
        )
        self.op_to_lambda[Type.BOOL][">="] = lambda x, y: Value(
            Type.BOOL, bool(int(x.value()) >= int(y.value()))
        )
        self.op_to_lambda[Type.BOOL]["<"] = lambda x, y: Value(
            Type.BOOL, bool(int(x.value()) < int(y.value()))
        )
        self.op_to_lambda[Type.BOOL]["<="] = lambda x, y: Value(
            Type.BOOL, bool(int(x.value()) <= int(y.value()))
        )

        #  set up operations on nil
        self.op_to_lambda[Type.NIL] = {}
        self.op_to_lambda[Type.NIL]["=="] = lambda x, y: Value(
            Type.BOOL, x.type() == y.type() and x.value() == y.value()
        )
        self.op_to_lambda[Type.NIL]["!="] = lambda x, y: Value(
            Type.BOOL, x.type() != y.type() or x.value() != y.value()
        )
        # set up operation on functions
        self.op_to_lambda[Type.FUNC] = {}
        self.op_to_lambda[Type.FUNC]["=="] = lambda x, y: Value(
            Type.BOOL, id(x.value()) == id(y.value())
        ) if x.type() == y.type() else Value(Type.BOOL, False)
        self.op_to_lambda[Type.FUNC]["!="] = lambda x, y: Value(
            Type.BOOL, id(x.value()) != id(y.value())
        ) if x.type() == y.type() else Value(Type.BOOL, True)

        # set up operation on lambdas
        self.op_to_lambda[Type.LAMBDA] = {}
        self.op_to_lambda[Type.LAMBDA]["=="] = lambda x, y: Value(
            Type.BOOL, id(x.value()) == id(y.value())
        ) if x.type() == y.type() else Value(Type.BOOL, False)
        self.op_to_lambda[Type.LAMBDA]["!="] = lambda x, y: Value(
            Type.BOOL, id(x.value()) != id(y.value())
        ) if x.type() == y.type() else Value(Type.BOOL, True)


    def __do_if(self, if_ast):
        cond_ast = if_ast.get("condition")
        result = self.__eval_expr(cond_ast)
        if result.type() == Type.INT:
            result = Value(Type.BOOL, bool(result.value()))
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
                run_while = Value(Type.BOOL, bool(run_while.value()))
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
        if value_obj.type() == Type.LAMBDA:
            index = self.env.create_deep_copy_lamb(value_obj.value())
            value_obj = Value(Type.LAMBDA, index)
        return (ExecStatus.RETURN, value_obj)
