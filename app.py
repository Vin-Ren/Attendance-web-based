from argparse import ArgumentParser
import traceback
import json
from datetime import datetime
from flask import Blueprint, jsonify, render_template, request

from utils import time_parser, dictUpdater, json_serializer
from objectified_dict import ObjectifiedDict, Config, Opts
from attendance import AttendanceManager, AttendanceEntry


config = Config(time_format='%H:%M', 
                cacheFile='cached.json', 
                name_autocompletion_file='names.list', 
                fix_name_capitalizations=True, 
                time_limited=True, 
                record_late_submissions=False, 
                auto_save=True,
                permit_overwrite=False,
                overwrite_tracker_level=1)
global_opts = Opts(json={'dumps':{'default':json_serializer}, 
                         'dump':{'indent':2},'load':{}},
                   open={'encoding':'UTF-8'},
                   jsonify={},
                   flask={'render_template':{'config':config}})
attendanceData = AttendanceManager(filename=lambda:config.cacheFile, opts=global_opts, permit_overwrite=lambda:config.permit_overwrite, auto_save=lambda:config.auto_save, overwrite_tracker_level=lambda:config.overwrite_tracker_level, ip_rate_limit=lambda:config.ip_rate_limit)

attendance = Blueprint('attendance', __name__, url_prefix='/attendance')


def getCopyCandidates():
    return {'Copy all to clipboard':'\n'.join(['{}. {}, {}'.format(i+1, data['name'], data['status']) for i, data in enumerate(attendanceData.data)]), 
            'Copy names to clipboard':'\n'.join(['{}. {}'.format(i+1, name) for i, name in enumerate(attendanceData.recorded_names)])}


@attendance.route('/API/<string:endpoint>', methods=['GET', 'POST'])
def API(endpoint):
    endpoint = endpoint.lower()
    multiCapitalizeEachFirstLetterInWord = lambda list_str: [' '.join([(lambda s: s[0].upper()+s[1:].lower())(s) for s in _s.split(' ') if len(s)]) for _s in list_str] # john doe -> John Doe
    

    if endpoint == 'submission':
        try:
            data = dict(request.form)
            submission_time = datetime.now()
            if not data['name']:
                raise KeyError
            if config.fix_name_capitalizations:
                data['name'] = multiCapitalizeEachFirstLetterInWord([data['name']])[0]
            deltaTimeFromLimit = (config.time_limit - submission_time)
            if deltaTimeFromLimit.total_seconds() <= 0 and config.time_limited:
                if config.record_late_submissions:
                    attendanceData.add_entry(data['name'], data['status'], submission_time=submission_time, description="Terlambat", remote_addr=request.remote_addr, access_route=request.access_route)
                    return jsonify({'success': True, 'success_message':'Batas Waktu Telah Dilampaui, namun kehadiran anda dicatat.', 'alert_type':'warning'}, **global_opts.get('jsonify'))
                return jsonify({'success': False, 'reason':'Batas Waktu Telah Dilampaui.'}, **global_opts.get('jsonify'))
            attendanceData.add_entry(data['name'], data['status'], submission_time=submission_time, remote_addr=request.remote_addr, access_route=request.access_route)
        except KeyError:
            # traceback.print_exc()
            return jsonify({'success': False, 'reason':'Masukan Nama Anda Terlebih Dahulu'}, **global_opts.get('jsonify'))
        except AttendanceManager.Exceptions.OverwriteIsNotPermitted:
            return jsonify({'success':False, 'reason':'Kehadiran anda telah terdaftar sebelumnya'}, **global_opts.get('jsonify'))
        except AttendanceManager.Exceptions.RateLimited as exc:
            return jsonify({'success':False, 'reason':'Anda telah mengirimkan {} daftar hadir sebelumnya.'.format(exc.total_submission), 'alert_type':'secondary'}, **global_opts.get('jsonify'))
        except Exception as exc:
            traceback.print_exc()
            return jsonify({'success': False, 'reason':'Exception Caught', 'exception': [exc.__class__.__name__, exc.args]}, **global_opts.get('jsonify'))
        return jsonify({'success':True, 'success_message':'Kehadiranmu Dicatat Sebagai {}.'.format(data['status'])}, **global_opts.get('jsonify'))
    
    elif endpoint == 'collected':
        return jsonify({'attendance_data':attendanceData.data}, **global_opts.get('jsonify'))
    
    elif endpoint == 'copy_clipboard':
        return jsonify(getCopyCandidates(), **global_opts.get('jsonify'))
    
    elif endpoint == 'autocomplete_names':
        try:
            with open(config.name_autocompletion_file, 'r', **global_opts.get('open')) as f:
                names = [ln.split('#', 1)[0].strip() for ln in f.read().splitlines() if len(ln) and not ln.startswith('#')]
                if config.fix_name_capitalizations:
                    names = multiCapitalizeEachFirstLetterInWord(names)
            return jsonify({'names':names}, **global_opts.get('jsonify'))
        except FileNotFoundError:
            with open(config.name_autocompletion_file, 'w', **global_opts.get('open')) as f:
                f.write("# This is a comment\n# Anything on the right side of '#' sign will be ignored.\nExample name Foo\nJohn Doe\nSteve\nAlex # Say hi to them!!!\n\n# Empty lines would be ignored.\n")
            return jsonify({'success':False, 'reason':'Autocomplete source file (\'{}\') not found. Created a basic template.'.format(config.name_autocompletion_file)}, **global_opts.get('jsonify'))


@attendance.route('/')
def index():
    return render_template('index.html', title="Collective Absence", **global_opts.get('flask.render_template'))


@attendance.route('/collected')
def show_collected():
    return render_template('collected.html', title="Collected Attendance", attendance_data=attendanceData.data, copy_candidates=getCopyCandidates(), **global_opts.get('flask.render_template'))


def parseArguments():
    parser = ArgumentParser(__name__, description="Collective Presence Submission Site App.")
    
    general = parser.add_argument_group('General')
    general.add_argument('-t', '--time-limit', dest='time_limit', metavar='TIME_LIMIT', default='0', help='Set the time limit for presence collection. Can be of time format or +minutes. Ex: 12:12, +30, 15.30.')
    general.add_argument('--load-cached', dest='load_cached', action='store_true', help='Whether to load cached attendance or not.')
    general.add_argument('--disable-status', metavar='STATUSES_TO_DISABLE', dest='statusesToDisable', default='', type=lambda _s:_s.split(','), help="Disable given list of statuses. Format=status1[,status2[,status3....]]")
    general.add_argument('--record-late', dest='record_late', action='store_true', help="Record late entries.")
    general.add_argument('--ignore-record-late', dest='record_late', action='store_false', help="Ignore late entries.")
    general.add_argument('--permit-overwrite', dest='permit_overwrite', action='store_true', help="Permits overwrite on Attendance Manager. This means an entry could be overwritten.")
    general.add_argument('--do-not-permit-overwrite', dest='permit_overwrite', action='store_false', help="Does NOT Permit overwrite on Attendance Manager. This means entries couldn't be overwritten.")
    general.add_argument('--overwrite-tracker-level', dest='overwrite_tracker_level', choices=[0,1,2,3], type=lambda x:min(max(int(x),0),3), help="Tracks overwrite level. Higher is more intense. 0=No tracking, 1=Track changes with depth 1, 2=Track all changes, 3=Track all object(s).")
    general.add_argument('--ip-rate-limit', dest='ip_rate_limit', type=int, help="limit an ip to a specified number of submissions to attendance.py. Best is 1, as it would only evaluate the top level entries, and not the previous entries. For limiting previous entries, it is best to use '--do-not-permit-overwrite'.")
    
    development = parser.add_argument_group('Development')
    development.add_argument('--host', dest='host', default='0.0.0.0', help="Host to run the web server on. Default='0.0.0.0' AKA Localhost")
    development.add_argument('--port', dest='port', default=58082, type=int, help="Port to run the web server on. Default=58082")
    development.add_argument('-w', '--waitress', dest='use_waitress', action='store_true', help='Run the web server using waitress')
    development.add_argument('--threads', dest='threads', default=__import__('os').cpu_count()//2, help='Threads to run waitress on. Default={}'.format(__import__('os').cpu_count()//2))
    development.add_argument('-d', '--debug', dest='debug', action='store_true', help='Starts Web server (WSGI) in Debug. Does not have effect if waitress is used.')
    development.add_argument('-c', '--config', dest='config', action='append', type=lambda entry:entry.split('=',1), choices=list(config), help="ADVANCED USE ONLY. WARNING:Could potentially break the app, use at your own risks. Change config directly. \nFormat='-c key=value' Repeatable. Boolean True=[true,yes,1], Boolean False=[false,no,0], List type=seperate entries with ',' without space.".format())

    return parser.parse_args()


def main():
    from flask import Flask
    
    app = Flask(__name__)
    app.register_blueprint(attendance, url_prefix='/')
    
    args = parseArguments()

    # Processing args values
    # TODO: Make a limiter for ip
    if args.time_limit=='0':
        print('Running without time limit')
        config.time_limited = False
        config.time_limit = datetime.fromtimestamp(0)
    else:
        currtime = datetime.now() # make it accept something like +00:30 as until 30 minutes after now
        time_limit = time_parser(args.time_limit.strip('+'))
        if args.time_limit.startswith('+'): # assume everything passed as in minutes
            # plus_seconds_delta = time_limit.replace(year=1970,month=1,day=1) - datetime.fromtimestamp(0) # This doesn't work
            config.time_limit = datetime.fromtimestamp(currtime.timestamp()+int(args.time_limit.strip('+'))*60)
        else:
            config.time_limit = time_limit.replace(year=currtime.year, month=currtime.month, day=currtime.day)
        print("Time Limit: {}".format(config.time_limit.strftime(config.time_format)))
    
    
    if args.load_cached:
        attendanceData.load_file()
        print('Cache Loaded')

    if len(args.statusesToDisable) > 0:
        config.disabled_statuses = ["{}{}".format(s[0].upper(), s[1:].lower()) for s in args.statusesToDisable if len(s)]
        print("Disabled Statuses: {}".format(', '.join(config.disabled_statuses) if len(config.disabled_statuses) else '-'))

    if args.record_late:
        config.record_late_submissions = True

    if args.permit_overwrite:
        config.permit_overwrite = True
    
    if args.overwrite_tracker_level:
        config.overwrite_tracker_level = args.overwrite_tracker_level
    
    if args.ip_rate_limit:
        config.ip_rate_limit = args.ip_rate_limit

    if args.config is not None:
        box_width = 50
        print('\n┌'+' Manual Config Modifications '.center(box_width-2,'─')+'┐')
        for k,v in args.config:
            if isinstance(config.get(k), bool):
                v = True if v.lower() in ['true', 'yes','1'] else False if v.lower() in ['false', 'no', '0'] else None
            elif isinstance(config.get(k), int):
                v = int(v)
            elif isinstance(config.get('k'), (list, tuple)):
                v = v.split(',')
                
            if v is not None:
                config[k] = v
                print('│'+"{}:{} --> {}".format(k, v.__class__.__name__, v).center(box_width-2, ' ')+'│')
        print('└'+''.center(box_width-2,'─')+'┘\n')
        
    if args.use_waitress:
        import waitress
        waitress.serve(app=app, host=args.host, port=args.port, threads=args.threads)
    else:
        app.run(host=args.host, port=args.port, debug=args.debug)
    

if __name__ == '__main__':
    main()
