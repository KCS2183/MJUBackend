#include <atomic>
#include <condition_variable>
#include <cstdlib>
#include <iostream>
#include <mutex>
#include <thread>
#include <queue>

using namespace std;

const int NO_JOB = -1;

// �������� ���� ������ �����ϱ� ���� flag.
// boolean �̶�� �ϴ��� atomic ���� �ʱ� ������ atomic<bool> �� �̿��Ѵ�.
atomic<bool> quit(false);

// ���� �ڿ��� queue.
// ���� �ڿ��� �ִٸ� �̸� ��ȣ�ϱ� ���� mutex �� �־�� �Ѵ�.
// �׸��� ���� �ڿ��� ����(condition) �� ��ȭ�� ����� ���� condition_variable �� ����Ѵ�.
// condition_variable �� mutex �� �ݵ�� �ʿ��ϴ�.
// �׷��� �������� condition_variable �� mutex �ϳ��� ���� ���� ��Ȳ�� �ָ��� ��.
mutex queMutex;
condition_variable queFillable;
condition_variable queFilled;
queue<int> que;


// producer thread �� thread �Լ�
void producer() {
  cout << "Producer starting. Thread id: " << this_thread::get_id() << endl;

  // thread ���� flag �� ���� ������ ���� ��Ų��.
  while (quit.load() == false) {
    int job = rand() % 100;
    {
        unique_lock<mutex> ul(queMutex);
        que.push(job);
        queFillable.notify_one();
        cout << "Produced: " << job << endl;
    }
  }
  cout << "Producer finished" << endl;
}


// consumer thread �� thread �Լ�
void consumer() {
  cout << "Consumer starting. Thread id: " << this_thread::get_id() << endl;

  // thread ���� flag �� ���� ������ ���� ��Ų��.
  while (quit.load() == false) {
    int job;
    {
        unique_lock<mutex> ul(queMutex);
        while(que.empty()){
            queFillable.wait(ul);
        }
        job = que.front();
        que.pop();
        cout << "Consumed: " << job << endl;
    }
  }
  cout << "Consumer finshed" << endl;
}


int main() {
  cout << "Main thread started. Thread id: " << this_thread::get_id() << endl;

  // ���� �������� �ʱⰪ�� �����Ѵ�.
  srand(time(NULL));

  // producer/consumer �������� �ڵ��� ������ C++ �� ��ü
  thread t1(producer);
  thread t2(consumer);
  thread t3(producer);

  // ��������� �����Ű���� flag �� �Ҵ�.
  this_thread::sleep_for(chrono::seconds(5));
  quit.store(true);

  // thread.joinable() �� C++ �� thread ��ü�� �����Ǵ� OS �� thread �� �ִ����� Ȯ���ϴ� ���̴�.
  // OS �� thread �� ��������� �ʾҰų�, �̹� thread �� join �Ǿ��ų�,
  // �ƴϸ� �츮�� �ٷ����� �ʾ�����, OS thread �� detach �� ��� joinable() �� false �� ��ȯ�Ѵ�.
  // ���⼭�� �����尡 ������� ��츸 join() �� ȣ���ϱ� ���ؼ� ����Ѵ�.
  if (t1.joinable()) {
    t1.join();
  }

  // thread.joinable() �� C++ �� thread ��ü�� �����Ǵ� OS �� thread �� �ִ����� Ȯ���ϴ� ���̴�.
  // OS �� thread �� ��������� �ʾҰų�, �̹� thread �� join �Ǿ��ų�,
  // �ƴϸ� �츮�� �ٷ����� �ʾ�����, OS thread �� detach �� ��� joinable() �� false �� ��ȯ�Ѵ�.
  // ���⼭�� �����尡 ������� ��츸 join() �� ȣ���ϱ� ���ؼ� ����Ѵ�.
  if (t2.joinable()) {
    t2.join();
  }

  if (t3.joinable()){
    t3.join();
  }

  cout << "Main thread finished" << endl;
}