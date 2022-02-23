from faulthandler import disable
import json
from datetime import datetime
from flask import Blueprint, jsonify, render_template, url_for, request

dictUpdater = lambda dbase,dupdt:(lambda base,updater:[base.update(updater), base][-1])(dbase.copy(),dupdt)

class objectifiedDict(dict):
    def __getattribute__(self, name):
        try:
            return super().__getattribute__(name)
        except AttributeError:
            return super().__getitem__(name)

    def __setattr__(self, name, value):
        return super().__setitem__(name, value)


env = objectifiedDict(time_format='%H:%M', cacheFile='cached.json')
attendanceList = {}


attendance = Blueprint('attendance', __name__, url_prefix='/attendance')


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
    formats = ['%H:%M', '%H:%M:%S', '%d %b %H:%M', '%H %M', '%H %M %S', '%H']

    for format in formats:
        try:
            return datetime.strptime(s, format)
        except ValueError:
            pass
    return datetime.fromtimestamp(int(s))

@attendance.route('/API/<string:endpoint>', methods=['GET', 'POST'])
def API(endpoint):
    if endpoint.lower() == 'input':
        try:
            data = dict(request.form)
            # print(data)
            deltaTimeFromLimit = (env.time_limit - datetime.now())
            if not data['name']:
                raise KeyError
            if deltaTimeFromLimit.total_seconds() <= 0:
                # lateness = datetime.fromtimestamp(abs(deltaTimeFromLimit.total_seconds()))
                return jsonify({'success': False, 'reason':'Batas Waktu Telah Dilampaui.'})
            attendanceList[data['name']] = data['status']
            saveAttendance()
        except KeyError:
            return jsonify({'success': False, 'reason':'Masukan Nama Anda Terlebih Dahulu'})
        except Exception as exc:
            return jsonify({'success': False, 'reason':'Exception Caught', 'exception': [exc.__class__.__name__, exc.args]})
        return jsonify({'success':True, 'success_message':'Kehadiranmu Telah Dicatat Sebagai {}.'.format(data['status'])})
    elif endpoint.lower() == 'collection':
        return jsonify({'raw':attendanceList,'str': '\n'.join(['{}. {}, {}'.format(i+1, data[0], data[1]) for i, data in enumerate(attendanceList.items())])})


@attendance.route('/')
def index():
    return render_template('index.html', env=env, title="Collective Absence")


@attendance.route('/collected')
def show_collected():
    copyCandidates = {'Copy all to clipboard':'\n'.join(['{}. {}, {}'.format(i+1, data[0], data[1]) for i, data in enumerate(attendanceList.items())]),
                      'Copy names to clipboard':'\n'.join(['{}. {}'.format(i+1, name) for i, name in enumerate(attendanceList.keys())])}
    return render_template('collected.html', env=env, title="Collected Attendance", attendance=attendanceList, copyCandidates=copyCandidates)


if __name__ == '__main__':
    from argparse import ArgumentParser
    from flask import Flask
    
    parser = ArgumentParser(__name__, description="Absen Kolektif")
    
    parser.add_argument('time_limit', type=timeParser, help='Set the time limit for presence collection')
    parser.add_argument('--load-cached', dest='loadCached', action='store_true', help='Whether to load cached.json or not.')
    parser.add_argument('--disable-status', dest='statusesToDisable', default='', type=lambda _s:_s.split(','), help="Disable given list of statuses. Format=status1[,status2[,status3....]]")

    args = parser.parse_args()
    
    currtime = datetime.now()
    env.time_limit = args.time_limit.replace(year=currtime.year, month=currtime.month, day=currtime.day)
    # print(currtime, env.time_limit)

    if args.loadCached:
        attendanceList=loadCached()
        print('Cache Loaded')

    if len(args.statusesToDisable) > 0:
        env.disabled_statuses = ["{}{}".format(s[0].upper(), s[1:].lower()) for s in args.statusesToDisable]
        print("Disabled Statuses: {}".format(', '.join(env.disabled_statuses)))

    
    app = Flask(__name__)
    app.register_blueprint(attendance, url_prefix='/')
    app.run('0.0.0.0', 58082, debug=True)
    