import json
from datetime import datetime
from attrLinker import LinkManager

from utils import dictUpdater
from objectified_dict import ObjectifiedDict, Opts


class AttendanceEntry(ObjectifiedDict):
    @classmethod
    def load_from_data(cls, *args, edit_depth=None, extra={}, **kw):
        instance =  cls(*args, **kw, **extra)
        if edit_depth:
            instance.edit_depth = edit_depth
        return instance
        
    def __init__(self, name, status, submission_time, description='', previous=None, **kw):
        super().__init__(name=name, status=status, submission_time=submission_time, description=description, extra=kw)
        if previous is not None:
            self.previous=previous
    
    @property
    def previous_depth(self):
        return self.getDepth(self)
    
    def __repr__(self):
        return "<{} Name={} EditDepth={}>".format(self.__class__.__name__, self.name, self.previous_depth)
    
    def get_json(self, **kw):
        return json.dumps(self, **kw)

    @staticmethod
    def getDepth(entry):
        '''Given an AttendanceEntry object, returns its 'previous' key depth.'''
        depth = 0
        while entry.get('previous') is not None:
            # Only if you preserve edit_depth every edit on overwrite_tracker_level 3.
            # if entry.get('edit_depth') is not None:
            #     depth+=entry.get('edit_depth')
            #     return depth
            entry = entry.get('previous')
            depth+=1
        return depth


class AttendanceManager:
    
    class Exceptions:
        class BaseExc(Exception):
            pass
        class OverwriteIsNotPermitted(BaseExc):
            pass
        class RateLimited(BaseExc):
            def __init__(self, *args, total_submission=0):
                self.total_submission = total_submission
                super().__init__(*args)
        class AccessRouteLimited(RateLimited):
            pass
        class IPAccesslimited(RateLimited):
            pass
    
    @classmethod
    def load_from_file(cls, filename, **kw):
        return cls(filename=filename, load_file=True, **kw)

    def __init__(self, filename, opts, permit_overwrite=True, load_file=False, auto_save=True, overwrite_tracker_level=1, ip_rate_limit=-1):
        self.data = []
        self._add_entry_hooks = []
        self.opts = dictUpdater(Opts(), opts)
        
        # TODO: Change all 5 of this. instead of passed as a parameter, pass Config object instead, then use attr binder to bind to AttendanceManager.
        self._filename = filename
        self._permit_overwrite = permit_overwrite
        self._auto_save = auto_save
        self._overwrite_tracker_level = overwrite_tracker_level
        self._ip_rate_limit = ip_rate_limit
        
        
        self.auto_save_hook = lambda *_, **__: self.save()
        
        # Tracer level is intensity of tracking overwrites in previous. Higher is more intense
        # TODO: Move tracker to another section or file.
        # Higher is more intense. 
        # 0=No tracking, 
        # 1=Track changes with depth 1, 
        # 2=Track all changes, 
        # 3=Track all object(s).
        self.tracker_hooks = {0: lambda *_,**__: None, 
                              1: lambda prev: dict(status=prev['status'], submission_time=prev['submission_time'], description=prev['description']),
                              2: lambda prev: dict(status=prev['status'], submission_time=prev['submission_time'], description=prev['description'], previous=prev.get('previous')),
                            #   3: lambda prev: prev
                              3: lambda prev: [prev.pop('edit_depth') if 'edit_depth' in prev else None, prev][-1]
                              }
        
        if load_file:
            self.load_file()

    @property
    def add_entry_hooks(self):
        hooks = self._add_entry_hooks
        hooks.append(self.auto_save_hook) if self.auto_save else None
        return hooks


    def load_file(self, filename=None):
        filename = filename or self.filename
        try:
            with open(filename, 'r', **self.opts.get('open')) as f:
                self.data = [AttendanceEntry.load_from_data(**entry) for entry in json.load(f, **self.opts.get('json.load'))]
                # print(self.data)
        except (FileNotFoundError, FileExistsError):
            pass

    def get_json(self):
        return json.dumps(self.data, **self.opts.get('json.dumps'))

    def save(self, filename=None):
        filename = filename or self.filename
        try:
            with open(filename, 'w', **self.opts.get('open')) as f:
                json.dump(self.data, f, **self.opts.get('json.dumps+json.dump'))
        except (FileNotFoundError, FileExistsError):
            pass
    
    @property
    def recorded_names(self):
        return [entry.name for entry in self.data]

    @property
    def recorded_ips(self):
        # Flatten if needed
        # return [ip for _l in [entry.extra.get('access_route') if entry.extra.get('remote_addr')=='127.0.0.1' else [entry.get('remote_addr')] for entry in self.data] for ip in _l]
        return [entry.extra.get('access_route')[-1] if entry.extra.get('remote_addr')=='127.0.0.1' else entry.get('remote_addr') for entry in self.data]
    
    def add_entry(self, name, *args, **kw):
        matches = [entry for entry in self.data if entry.name == name]
        if not self.permit_overwrite and len(matches):
            raise self.Exceptions.OverwriteIsNotPermitted('An entry with given name already exist in database.')
        for match in matches:
            self.data.remove(match)
            if match != matches[-1]:
                del match
        entry = AttendanceEntry(name, *args, **kw)
        
        if self.ip_rate_limit > 0:
            requester_ip = entry.extra.get('access_route')[-1] if entry.extra.get('remote_addr')=='127.0.0.1' else entry.extra.get('remote_addr')
            count = self.recorded_ips.count(requester_ip)
            # print("Recorded IPs:{} RequesterIP={} RecurringIPCount={}".format(self.recorded_ips, requester_ip, count)) # For Debug TBD
            if count>=self.ip_rate_limit:
                raise self.Exceptions.IPAccesslimited('More than {} submissions detected inside the database from given ip.'.format(self.ip_rate_limit), total_submission=count)
        
        if matches:     
            entry.previous = self.tracker_hooks.get(self.overwrite_tracker_level)(matches[0])
            if self.overwrite_tracker_level > 1:
                entry.edit_depth = entry.previous_depth
            
        self.data.append(entry)
        [hook(entry) for hook in self.add_entry_hooks]
        # print(self.data)
        

# If calls given value if callable(AKA Function or instance with __call__ method) else return it
optional_callable = lambda val:val() if callable(val) else val
apply_optcall = lambda e: LinkManager._getDefault().bind(AttendanceManager, e[0], e[1], getterConverter=optional_callable, setupOptions=dict(enableSetter=False))
list(map(apply_optcall,
         {'_permit_overwrite': 'permit_overwrite',
          '_auto_save': 'auto_save',
          '_filename': 'filename',
          '_overwrite_tracker_level':'overwrite_tracker_level',
          '_ip_rate_limit':'ip_rate_limit'}.items()))
