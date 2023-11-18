# The EnvironmentManager class keeps a mapping between each variable name (aka symbol)
# in a brewin program and the Value object, which stores a type, and a value.
import copy
from type_valuev2 import Value
class EnvironmentManager:
    def __init__(self):
        self.environment = [{}]

    def deepcopy(self):
        newEnv = EnvironmentManager()
        newEnv.environment = copy.deepcopy(self.environment)

        return newEnv

    # returns a VariableDef object
    def get(self, symbol, save_env= None):
        for env in reversed(self.environment):
            if symbol in env:
                return env[symbol]

        return None
    
    # here symbol would be the 
    def get_ref(self, symbol, original_var, save_env = None, it = 0):
        for env in list(reversed(self.environment))[it:]:
            if original_var+"!REF!" in env:
                return env[original_var+"!REF!"]
            elif symbol in env:
                if isinstance(env[symbol], list):
                    # print("FROM GET REF symbol", symbol, "AND ORIGINAL VAR", original_var)
                    if(symbol == original_var):
                        return self.get_ref(symbol, original_var, save_env, it+1)
                    else:
                        return env[symbol]
                else:
                    return env[symbol]
        if save_env:
            for env in reversed(save_env.environment):
                if symbol in env:
                    return env[symbol]


    #val represents the list of [Value, refvar name]
    def set_ref(self, key, value, var_name, save_env = None, it = 0):
        # print("FROM SET_REF", value)
        # save_env only passed when its a lambda
        if save_env != None:
            new_lambda = Value(value.type(), value.value())
            if var_name:
                self.set(var_name+"!REF!", new_lambda)
            for env in reversed(save_env.environment):
                if key in env:
                    env[key] = new_lambda
            print("FROM SET REF ENV", self.environment)
            print("FROM SET REF SAVE ENV",save_env.environment)
                    # print("FROM SET_REF NEW SAVE ENV", save_env)
                    
        
        else:
            for env in list(reversed(self.environment))[1+it:]:
                if key in env:
                    if isinstance(env[key], list):
                        val = env[key]
                        if isinstance(env[key], list):
                            self.set_ref(val[1], value, var_name, save_env, it + 1)
                    else:
                        env[key] = value
                        return




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

    def get_ref_var(self, save_env):
        ref_dict = {}
        print("FROM GET REF VAR SAVE ENV", save_env.environment)
        for env in save_env.environment:
            for key, value in env.items():
                if key[-5:] == "!REF!":
                    ref_dict[key[:-5]] = value
        return ref_dict

