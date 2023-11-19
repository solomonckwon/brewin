# The EnvironmentManager class keeps a mapping between each variable name (aka symbol)
# in a brewin program and the Value object, which stores a type, and a value.

import copy
from type_valuev2 import Type, Value
class EnvironmentManager:
    lambda_call = 0
    lambda_indexes = []
    def __init__(self):
        self.environment = [{}]
        self.lambda_environment = []
        self.temp_environment = []

    # returns a VariableDef object
    def get(self, symbol):
        for env in reversed(self.environment):
            if symbol in env:
                return env[symbol]

        return None

    def set(self, symbol, value):
        for env in reversed(self.environment):
            if symbol in env:
                env[symbol] = value
                return

        # symbol not found anywhere in the environment
        self.environment[-1][symbol] = value

    # create a new symbol in the top-most environment, regardless of whether that symbol exists
    # in a lower environment
    def create(self, symbol, value):
        self.environment[-1][symbol] = value

    # used when we enter a nested block to create a new environment for that block
    def push(self):
        self.environment.append({})  # [{}] -> [{}, {}]

    # used when we exit a nested block to discard the environment for that block
    def pop(self):
        self.environment.pop()

    # index 0 will be closure environment
    # index 1 will be lambda_ast
    # ....
    # index n will be closure
    # index n+1 will be lambda_ast
    def push_lambda_env(self, lambda_ast):
        closure = copy.deepcopy(self.environment)
        self.lambda_environment.append(closure)
        self.lambda_environment.append(lambda_ast)
        # print(lambda_ast)
        ## return the index of the lambdas closure env
        return (len(self.lambda_environment) - 2)
    
    # For when a lambda function is called
    def set_lamb_env(self, env_index):
        self.lambda_indexes.append(env_index)
        if self.lambda_call == 0:
            self.temp_environment = self.environment
            self.environment = self.lambda_environment[env_index]
        self.lambda_call += 1
        
    # gets the lambda_ast
    def get_lamb_ast(self, env_index):
        return self.lambda_environment[env_index+1]
    
    def create_deep_copy_lamb(self, to_copy_index):
        closure = copy.deepcopy(self.lambda_environment[to_copy_index])
        self.lambda_environment.append(closure)
        lambda_ast = copy.deepcopy(self.get_lamb_ast(to_copy_index))
        self.lambda_environment.append(lambda_ast)
        return (len(self.lambda_environment) - 2)
        
    # changes environment back to the main env
    # WHEN A ENDS IT SETS THIS
    def set_main_env(self):
        self.lambda_call -= 1
        if self.lambda_call == 0:
            self.lambda_environment[self.lambda_indexes.pop()] = self.environment
            self.environment = self.temp_environment
        else:
            self.lambda_indexes.pop()

            

    def set_ref(self, var_name, value):
        # if in lambda, ref args must be looking for the referenced variable in the main env
        print(self.environment)
        print(self.temp_environment)
        print("____SET_REF___")
        if self.lambda_call > 0:
            for env in reversed(self.environment):
                if var_name in env:
                    if env[var_name].type() == Type.REFARG:
                        var_name = env[var_name].value()
                        break
                    else:
                        env[var_name] = value

            for env in reversed(self.temp_environment):
                if var_name in env:
                    if env[var_name].type() == Type.REFARG:
                        var_name = env[var_name].value()
                    else:
                        env[var_name] = value
        else:
            for env in reversed(self.environment):
                if var_name in env:
                    if env[var_name].type() == Type.REFARG:
                        var_name = env[var_name].value()
                    else:
                        # print(env[var_name])
                        env[var_name] = value
                        # print(env[var_name])
                    


        print(self.environment)
        print(self.temp_environment)
        print()

    def get_ref(self, var_name):
        # print(self.environment)
        # print(self.temp_environment)
        # print("____GET_REF____")
        return_value = None
        if self.lambda_call > 0:
            for env in reversed(self.environment):
                if var_name in env:
                    if env[var_name].type() == Type.REFARG:
                        var_name = env[var_name].value()
                        # break
                    else:
                        # print(env[var_name])
                        return_value = env[var_name]
                    
            for env in reversed(self.temp_environment):
                if var_name in env:
                    if env[var_name].type() == Type.REFARG:
                        var_name = env[var_name].value()
                    else:
                        return_value = env[var_name]
        else:
            # print()
            for env in reversed(self.environment):
                if var_name in env:
                    if env[var_name].type() == Type.REFARG:
                        var_name = env[var_name].value()
                    else:
                        return_value = env[var_name]

        # print(self.environment)
        # print(self.temp_environment)
        # print(return_value)
        # print()
        
        return return_value
    
    def check_for_ref(self, var_name):
        for env in reversed(self.environment):
            for key, val in env.items():
                if val.value() == var_name:
                    return key
