from flask import Flask, request,render_template
import json,time
from apscheduler.schedulers.background import BackgroundScheduler

app=Flask(__name__)
global w,frame
frame={"frame":["1","2"]}
w={"send":[]}

def tt():
    l=w["send"]
    l.append(time.strftime("%Y-%m-%d %H:%M:%S"))
    w["send"]=l

@app.route('/window',methods=['POST','GET'])
def refres():
    if request.method=='POST':
        print(request.get_data())
        if request.get_data()==b"window":
            return json.dumps(w)
        else:
            return json.dumps(frame)


@app.route('/',methods=['POST','GET'])
def refresh():
    if request.method=='POST':
        return json.dumps(w)
    else:
        return render_template('testapi.html')

if __name__=='__main__':
    job = BackgroundScheduler(timezone='utc')
    job.start()
    job.add_job(tt,'interval',seconds=5,id='-1')
    app.run(host='127.0.0.1',port=80,debug=True,threaded=True)