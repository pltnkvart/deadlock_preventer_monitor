import random
import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from deadlock_prevent_monitor import DeadlockPreventerMonitor
from logger import logger
from thread import WorkerThread


class SimulationRunner:
    def __init__(self, resource_config, resource_names, max_processes):
        self.resource_config = resource_config
        self.resource_names = resource_names
        self.process_range = range(2, max_processes + 1)
        self.results = []

    def run_simulation(self, num_processes):
        """Запускает одну симуляцию для заданного числа процессов."""

        # Список для сбора времени ожидания каждого потока
        wait_times = []

        # Нужно немного изменить WorkerThread, чтобы он мог возвращать время ожидания
        class ReportingWorkerThread(WorkerThread):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.total_wait_time = 0

            def run(self):
                # Переопределяем метод run, чтобы измерять время

                logger.info(self.process_id, "Запущен.")
                self.monitor.set_max_claim(self.process_id, self.max_claim)

                for _ in range(random.randint(2, 4)):
                    time.sleep(random.uniform(0.1, 0.5))  # Уменьшим для скорости теста
                    needed = self.max_claim - self.currently_allocated
                    if np.all(needed == 0):
                        break
                    request = [random.randint(0, n) if n > 0 else 0 for n in needed]
                    request = np.array(request, dtype=int)
                    if np.all(request == 0):
                        continue

                    # --- Измерение времени ожидания ---
                    request_start_time = time.time()

                    # Изменим цикл, чтобы он возвращал True/False
                    # и мы могли продолжать замерять время.
                    is_granted = False
                    while not is_granted:
                        is_granted = self.monitor.request_resources(self.process_id, request)
                        if not is_granted:
                            time.sleep(random.uniform(0.1, 0.2))  # Короткая пауза перед повторной попыткой

                    request_end_time = time.time()
                    self.total_wait_time += request_end_time - request_start_time
                    # ------------------------------------

                    self.currently_allocated += request
                    time.sleep(random.uniform(0.1, 0.5))

                    if np.any(self.currently_allocated > 0):
                        release = [random.randint(0, a) for a in self.currently_allocated]
                        release = np.array(release, dtype=int)
                        if np.any(release > 0):
                            self.monitor.release_resources(self.process_id, np.array(release))
                            self.currently_allocated -= np.array(release)

                if np.any(self.currently_allocated > 0):
                    self.monitor.release_resources(self.process_id, self.currently_allocated)

                wait_times.append(self.total_wait_time)
                logger.info(self.process_id, "Завершен.")

        monitor = DeadlockPreventerMonitor(self.resource_config, num_processes)

        threads = []
        for i in range(num_processes):
            max_claim = [random.randint(2, self.resource_config[j]) for j in range(len(self.resource_config))]
            thread = ReportingWorkerThread(i, monitor, max_claim)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        return sum(wait_times) / len(wait_times) if wait_times else 0

    def start_tests(self):
        """Запускает серию тестов для разного количества процессов."""
        print("\n" + "=" * 50)
        print("Начинаем тестирование производительности...")
        for n_proc in self.process_range:
            print(f"Тестируем с {n_proc} процессами...")
            # Можно запустить несколько раз для усреднения
            avg_wait = self.run_simulation(n_proc)
            self.results.append({"num_processes": n_proc, "avg_wait_time": avg_wait})

        print("Тестирование завершено.")
        return pd.DataFrame(self.results)

    @staticmethod
    def plot_results(df):
        """Строит график по результатам."""
        plt.style.use("seaborn-v0_8-whitegrid")
        fig, ax = plt.subplots(figsize=(10, 6))

        ax.plot(df["num_processes"], df["avg_wait_time"], marker="o", linestyle="-", color="b")

        ax.set_title("Зависимость среднего времени ожидания от количества процессов", fontsize=16)
        ax.set_xlabel("Количество процессов", fontsize=12)
        ax.set_ylabel("Среднее время ожидания (сек)", fontsize=12)

        plt.tight_layout()
        plt.savefig("wait_time_vs_processes.png")
        print("\nГрафик сохранен в файл 'wait_time_vs_processes.png'")
        plt.show()


if __name__ == "__main__":
    # --- Запуск тестирования и построение графика ---
    TOTAL_RESOURCES = [10, 7, 12]
    RESOURCE_NAMES = ["CPU", "RAM", "Disk"]

    # Запускаем симуляцию для N процессов от 2 до 10
    runner = SimulationRunner(TOTAL_RESOURCES, RESOURCE_NAMES, max_processes=10)
    results_df = runner.start_tests()

    # Выводим таблицу с результатами
    print("\nРезультаты тестирования:")
    print(results_df)

    # Строим график
    runner.plot_results(results_df)
