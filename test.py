import threading
import time

# A sample function to print squares
def print_squares(thread_name, numbers):

   for number in numbers:
       print(thread_name, number)
       
       # Produce some delay to see the output
       # syntax: time.sleep(<time in seconds : float>)
       time.sleep(1)

thread1 = threading.Thread(target=print_squares, args=("thread1", [1, 2, 3, 4, 5]))
thread2 = threading.Thread(target=print_squares, args=("thread2", [6, 7, 8, 9, 10]))
thread3 = threading.Thread(target=print_squares, args=("thread3", [11, 12, 13, 14, 15]))

thread1.start()
thread2.start()
thread3.start()

thread1.join()
thread2.join()
thread3.join()