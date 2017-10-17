from utilities import *
import signal
import os
import time
from multiprocessing import Process, Queue

def executeInProcessGroup(task):
    os.setpgid(0,0)
    task.q.put(task.command(*task.arguments))


class TimeshareTask():
    def __init__(self, command, arguments, logScore = 0):
        self.logScore = logScore
        self.running = False
        self.finished = False
        self.command = command
        self.arguments = arguments
        self.q = Queue()
        self.process = None

    def execute(self,dt):
        if self.finished: return "finished"
        if not self.running:
            self.process = Process(target = executeInProcessGroup, args = (self,))
            self.process.start()
            print "timeshare child PID:",self.process.pid
            os.setpgid(self.process.pid,self.process.pid)
            print "timeshare process group",os.getpgid(self.process.pid)
            assert os.getpgid(self.process.pid) == self.process.pid
            print "my process group",os.getpgrp(),"which should be",os.getpgid(0)
            assert os.getpgid(self.process.pid) != os.getpgid(0)
            self.running = True
        else:
            os.killpg(self.process.pid, signal.SIGCONT)
        
        self.process.join(dt)
        if self.process.is_alive():
            os.killpg(self.process.pid, signal.SIGSTOP)
            return "still running"
        else:
            self.finished = True
            return self.q.get()

    def cleanup(self):
        if self.process != None and self.process.is_alive():
            os.killpg(self.process.pid, signal.SIGKILL)


def executeTimeshareTasks(tasks, dt = 1):
    while len(tasks) > 0:
        bestScore = max([ t.logScore for t in tasks ])
        denominator = sum([ math.exp(t.logScore - bestScore) for t in tasks ])
        finished = []
        for task in tasks:
            w = dt*math.exp(t.logScore - bestScore)/denominator
            result = task.execute(w)
            if result == "still running": continue
            elif result == "finished": assert False
            else:
                yield result
                finished.append(task)
        tasks = [ t for t in tasks if not t in finished ]
    
if __name__ == "__main__":
    def callback():
        os.system("wget http://archive.ubuntu.com/ubuntu/dists/zesty/main/installer-amd64/current/images/netboot/mini.iso")
        return "returning a value!"
    for result in executeTimeshareTasks([TimeshareTask(callback,[]),TimeshareTask(callback,[])]):
        print result