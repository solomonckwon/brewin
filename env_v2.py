# The EnvironmentManager class keeps a mapping between each variable name (aka symbol)
# in a brewin program and the Value object, which stores a type, and a value.
class EnvironmentManager:
    def __init__(self):
        self.environment = [{}]

    # returns a VariableDef object
    def get(self, symbol):
        for env in reversed(self.environment):
            if symbol in env:
                return env[symbol]

        return None
    
    def get_ref(self, symbol, save_env = None, it = 0):
        for env in list(reversed(self.environment))[(1+it):]:
            if symbol in env:
                return env[symbol]

        if save_env:
            for env in reversed(save_env.environment):
                if symbol in env:
                    return env[symbol]
        return


    def set_ref(self, symbol, value, save_env = None, it = 0):

        # save_env only passed when its a lambda
        
        for env in list(reversed(self.environment))[1+it:]:
            if symbol in env:
                if isinstance(env[symbol], list):
                    val = env[symbol]
                    if isinstance(env[symbol], list):
                        self.set_ref(val[1], value, save_env, it + 1)
                else:
                    env[symbol] = value
                    return

        if save_env:
            for env in reversed(save_env.environment):
                if symbol in env:
                    env[symbol] = value
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