import atexit
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

env = objectifiedDict(time_format='%H:%M')
attendanceList = {}


def loadCached():
    try:
        with open('cached.json', 'r') as f:
            return json.load(f)
    except:
        pass


attendance = Blueprint('attendance', __name__, url_prefix='/attendance')


def saveAttendance():
    with open('cached.json', 'w') as f:
        json.dump(attendanceList, f, indent=2)
atexit.register(saveAttendance)

def timeParser(s:str):
    formats = ['%H:%M', '%H:%M:%S', '%d %b %H:%M', '%H %M', '%H %M %S']

    for format in formats:
        try:
            return datetime.strptime(s, format)
        except ValueError:
            pass
    return datetime.fromtimestamp(int(s))

@attendance.route('/input', methods=['POST'])
def inputAPI():
    try:
        data = dict(request.form)
        # print(data)
        deltaTimeFromLimit = (env.time_limit - datetime.now())
        if not data['name']:
            raise KeyError
        if deltaTimeFromLimit.total_seconds() <= 0:
            lateness = datetime.fromtimestamp(abs(deltaTimeFromLimit.total_seconds()))
            return jsonify({'success': False, 'reason':'Batas Waktu Telah Dilampaui.'})
        attendanceList[data['name']] = data['status']
        saveAttendance()
    except KeyError:
        return jsonify({'success': False, 'reason':'Tolong Masukan Nama Anda'})
    except Exception as exc:
        return jsonify({'success': False, 'reason':'Exception Caught', 'exception': [exc.__class__.__name__, exc.args]})
    return jsonify({'success':True, 'success_message':'Kehadiranmu Telah Tercatat Sebagai {}.'.format(data['status'])})


@attendance.route('/')
def index():
    return render_template('index.html', env=env)

if __name__ == '__main__':
    from argparse import ArgumentParser
    from flask import Flask
    parser = ArgumentParser(__name__, description="Absen Kolektif")
    parser.add_argument('time_limit', type=timeParser, help='Set the time limit for presence collection')
    parser.add_argument('--load-cached', dest='loadCached', action='store_true', help='Whether to load cached.json or not.')
    args = parser.parse_args()
    if args.loadCached:
        attendanceList=loadCached()
        print('Cache Loaded')
    currtime = datetime.now()
    env.time_limit = args.time_limit.replace(year=currtime.year, month=currtime.month, day=currtime.day)
    print(currtime, env.time_limit)
    
    app = Flask(__name__)
    app.register_blueprint(attendance, url_prefix='/')
    app.run('0.0.0.0', 58082, debug=True)