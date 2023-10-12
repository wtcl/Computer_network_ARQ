import time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor


def my_job(name):
    print(name,time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())))

job=BackgroundScheduler(timezone='utc')
job.add_job(my_job,'interval', seconds=5,id=str(-1),args=['-1'])
job.start()
for i in range(10):
    job.add_job(my_job,trigger='interval', seconds=10,id=str(i),args=[str(i)])
    time.sleep(1)
for i in range(10):
    job.remove_job(str(i))
