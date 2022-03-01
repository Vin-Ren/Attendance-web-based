from utils import dictUpdater


class ObjectifiedDict(dict):
    def __getattribute__(self, name):
        try:
            return super().__getattribute__(name)
        except AttributeError:
            return super().__getitem__(name)

    def __setattr__(self, name, value):
        return super().__setitem__(name, value)
    
    def update(self, other):
        for k,v in other.items():
            self.__setitem__(k,v)


class Opts(ObjectifiedDict):
    def _get(self, accessor, defaultValue=None):
        '''
        To ease access to nested opts. More similiar to dictionary's get function.
        "Opts.get('json.dump')" Instead of "self.opts.get('json', {}).get('dump', defaultValue)"
        '''
        opts=self
        for level_accessor in [lv_acc for lv_acc in accessor.split('.') if len(lv_acc)]:
            try:
                opts = opts.__getitem__(level_accessor)
                # print("{} -> {}".format(level_accessor, opts)) # For Debug TBD
            except (KeyError, TypeError):
                return defaultValue
        return opts

    def get(self, accessors):
        '''
        To ease access to nested opts. 
        "Opts.get('json.dump')" Instead of "self.opts.get('json', {}).get('dump', {})"
        
        Also, supports multiple opts combination, like:
        "Opts.get('Foo.base+Foo.custom1')" Instead of 
        "FooBase = Opts.get('Foo.custom1')
        FooBase.update(Opts.get('Foo.base'))"
        this '+' Combiner is only valid for types=[dict, list, tuple, int, float, str]
        For multiple opts, which values are of dict type, the order matters, the previous would be overwritten by the next, the order is from left to right.
        For values of array-like object like list,tuple,str, it would use the + operator.
        For other primordial types, such as int,float, the '+' operator would be used.
        '''
        aggregated = {dict:{}, list:[], tuple:(), int:0, float:float(0.0), str:''}
        for accessor in [acc for acc in accessors.split('+') if len(acc)]:
            value = self._get(accessor, defaultValue={})
            # print("{} --> {}".format(accessor, value)) # For Debug TBD
            if isinstance(value, dict):
                dictUpdater(aggregated[dict], value)
            elif isinstance(value, (list, tuple, int, float, str)):
                aggregated[type(value)]+=value
        aggregated = [sub for sub in aggregated.values() if sub]
        res = (aggregated+[{}])[0] # +[{}] empty dict for default value, if nothing was aggregated, to evade TypeError
        # print("{} ---> {}".format(accessors, res)) # For Debug TBD
        return res
            

class Config(ObjectifiedDict):
    def __repr__(self):
        return "<{} With {} Configurations>".format(self.__class__.__name__, self.__len__())

