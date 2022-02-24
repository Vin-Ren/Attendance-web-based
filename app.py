from argparse import ArgumentParser
import json
from datetime import datetime
from flask import Blueprint, jsonify, render_template, request


dictUpdater = lambda dbase,dupdt:(lambda base,updater:[base.update(updater), base][-1])(dbase.copy(),dupdt)


class objectifiedDict(dict):
    def __getattribute__(self, name):
        try:
            return super().__getattribute__(name)
        except AttributeError:
            return super().__getitem__(name)

    def __setattr__(self, name, value):
        return super().__setitem__(name, value)


env = objectifiedDict(time_format='%H:%M', cacheFile='cached.json', name_autocompletion_file='names.json', fix_name_capitalizations=True, time_limited=True)
attendanceList = {}


def loadCached():
    try:
        with open(env.cacheFile, 'r') as f:
            return json.load(f)
    except:
        pass


def saveAttendance():
    with open(env.cacheFile, 'w') as f:
        json.dump(attendanceList, f, indent=2)


def timeParser(s:str):
    formats = ['%H:%M', '%H:%M:%S', '%H %M', '%H %M %S', '%H', '%M']
    for _format in formats:
        try:
            return datetime.strptime(s, _format)
        except ValueError:
            # print(s, _format)
            pass
    return datetime.fromtimestamp(int(s))



attendance = Blueprint('attendance', __name__, url_prefix='/attendance')


@attendance.route('/API/<string:endpoint>', methods=['GET', 'POST'])
def API(endpoint):
    multiCapitalizeEachFirstLetterInWord = lambda list_str: [' '.join([(lambda s: s[0].upper()+s[1:].lower())(s) for s in _s.split(' ') if len(s)]) for _s in list_str] # john doe -> John Doe

    if endpoint.lower() == 'input':
        try:
            data = dict(request.form)
            # print(data)
            deltaTimeFromLimit = (env.time_limit - datetime.now())
            if not data['name']:
                raise KeyError
            if deltaTimeFromLimit.total_seconds() <= 0 and env.time_limited:
                # lateness = datetime.fromtimestamp(abs(deltaTimeFromLimit.total_seconds()))
                return jsonify({'success': False, 'reason':'Batas Waktu Telah Dilampaui.'})
            if env.fix_name_capitalizations:
                data['name'] = multiCapitalizeEachFirstLetterInWord([data['name']])[0]
            attendanceList[data['name']] = data['status']
            saveAttendance()
        except KeyError:
            return jsonify({'success': False, 'reason':'Masukan Nama Anda Terlebih Dahulu'})
        except Exception as exc:
            return jsonify({'success': False, 'reason':'Exception Caught', 'exception': [exc.__class__.__name__, exc.args]})
        return jsonify({'success':True, 'success_message':'Kehadiranmu Telah Dicatat Sebagai {}.'.format(data['status'])})
    elif endpoint.lower() == 'collection':
        return jsonify({'raw':attendanceList,'str': '\n'.join(['{}. {}, {}'.format(i+1, data[0], data[1]) for i, data in enumerate(attendanceList.items())])})
    elif endpoint.lower() == 'autocomplete_name':
        try:
            with open(env.name_autocompletion_file, 'r') as f:
                data = json.load(f)
                if env.fix_name_capitalizations:
                    data['names'] = multiCapitalizeEachFirstLetterInWord(data['names'])
            return jsonify(data)
        except FileNotFoundError:
            with open(env.name_autocompletion_file, 'w') as f:
                json.dump({'names':['ExampleNames','john doe','alex']}, f, indent=2)
            return jsonify({'success':False, 'reason':'Autocomplete source file ({}) not found. Created a basic template.'.format(env.name_autocompletion_file)})
        


@attendance.route('/')
def index():
    return render_template('index.html', env=env, title="Collective Absence")


@attendance.route('/collected')
def show_collected():
    copyCandidates = {'Copy all to clipboard':'\n'.join(['{}. {}, {}'.format(i+1, data[0], data[1]) for i, data in enumerate(attendanceList.items())]),
                      'Copy names to clipboard':'\n'.join(['{}. {}'.format(i+1, name) for i, name in enumerate(attendanceList.keys())])}
    return render_template('collected.html', env=env, title="Collected Attendance", attendance=attendanceList, copyCandidates=copyCandidates)


def parseArguments():
    parser = ArgumentParser(__name__, description="Absen Kolektif")
    
    parser.add_argument('-t', '--time_limit', dest='time_limit', metavar='TimeLimit', default='0', help='Set the time limit for presence collection')
    parser.add_argument('--load-cached', dest='loadCached', action='store_true', help='Whether to load cached.json or not.')
    parser.add_argument('--disable-status', metavar='STATUSES_TO_DISABLE', dest='statusesToDisable', default='', type=lambda _s:_s.split(','), help="Disable given list of statuses. Format=status1[,status2[,status3....]]")
    parser.add_argument('--host', dest='host', default='0.0.0.0', help="Host to run the web server on. Default='0.0.0.0' AKA Localhost")
    parser.add_argument('--port', dest='port', default=58082, type=int, help="Port to run the web server on. Default=58082")
    parser.add_argument('-w', '--waitress', dest='use_waitress', action='store_true', help='Run the web server using waitress')
    parser.add_argument('--threads', dest='threads', default=__import__('os').cpu_count()//2, help='Threads to run waitress on. Default={}'.format(__import__('os').cpu_count()//2))
    parser.add_argument('-d', '--debug', dest='debug', action='store_true', help='Starts Web server in Debug')

    return parser.parse_args()


def main():
    from flask import Flask
    
    app = Flask(__name__)
    app.register_blueprint(attendance, url_prefix='/')
    
    args = parseArguments()

    # Processing args values

    if args.time_limit=='0':
        print('Running without time limit')
        env.time_limited = False
        env.time_limit = datetime.fromtimestamp(0)
    else:
        currtime = datetime.now() # make it accept something like +00:30 as until 30 minutes after now
        time_limit = timeParser(args.time_limit.strip('+'))
        if args.time_limit.startswith('+'): # assume everything passed as in minutes
            # plus_seconds_delta = time_limit.replace(year=1970,month=1,day=1) - datetime.fromtimestamp(0) # This doesn't work
            env.time_limit = datetime.fromtimestamp(currtime.timestamp()+int(args.time_limit.strip('+'))*60)
        else:
            env.time_limit = time_limit.replace(year=currtime.year, month=currtime.month, day=currtime.day)
        print("Time Limit: {}".format(env.time_limit.strftime(env.time_format)))
    # print(currtime, env.time_limit)

    if args.loadCached:
        global attendanceList
        attendanceList=loadCached()
        print('Cache Loaded')

    if len(args.statusesToDisable) > 0:
        env.disabled_statuses = ["{}{}".format(s[0].upper(), s[1:].lower()) for s in args.statusesToDisable if len(s)]
        print("Disabled Statuses: {}".format(', '.join(env.disabled_statuses) if len(env.disabled_statuses) else '-'))

    if args.use_waitress:
        import waitress
        waitress.serve(app=app, host=args.host, port=args.port, threads=args.threads)
    else:
        app.run(host=args.host, port=args.port, debug=args.debug)
    

if __name__ == '__main__':
    main()
