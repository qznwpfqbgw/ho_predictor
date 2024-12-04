import threading
import time

def task():
    print("Thread started")
    time.sleep(2)
    print("Thread ended")

t = threading.Thread(target=task)
t.start()  # 非阻塞
print("Main thread continues")  # 這行會立即執行，不等待 t 結束