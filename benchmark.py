import threading
import time

import matplotlib.pyplot as plt
import numpy as np

# Импортируем ваш основной класс
from deadlock_prevent_monitor import DeadlockPreventerMonitor


# ==============================================================================
# 1. ЗАГЛУШКА ДЛЯ ЛОГГЕРА, ЧТОБЫ I/O НЕ ВЛИЯЛ НА РЕЗУЛЬТАТЫ
# ==============================================================================
class DummyLogger:
    """Логгер, который ничего не делает. Нужен для "чистых" бенчмарков."""

    def __getattr__(self, name):
        return lambda *args, **kwargs: None


# ==============================================================================
# 2. МИКРО-БЕНЧМАРК: ИЗМЕРЕНИЕ НАКЛАДНЫХ РАСХОДОВ (_is_safe_state)
# ==============================================================================


def generate_random_state(num_processes, total_resources):
    """Генерирует случайное состояние системы для одного теста."""
    monitor = DeadlockPreventerMonitor(total_resources, num_processes, matrix_logger=DummyLogger())
    max_claim = np.random.randint(
        1, np.array(total_resources, dtype=int) + 1, size=(num_processes, len(total_resources))
    )
    for i in range(num_processes):
        monitor.set_max_claim(i, max_claim[i])

    for i in range(num_processes):
        if np.random.rand() > 0.5:
            request = np.floor_divide(monitor.need[i], 2)
            request = np.minimum(request, monitor.available)
            monitor.available -= request
            monitor.allocation[i] += request
            monitor.need[i] -= request
    return monitor


def benchmark_overhead(monitor, iterations=1000):
    """Измеряет среднее время выполнения _is_safe_state."""
    total_time = 0
    process_id_to_test = 0
    request_to_test = (
        np.floor_divide(monitor.need[process_id_to_test], 2)
        if np.any(monitor.need[process_id_to_test] > 0)
        else np.array([0] * monitor.num_resources)
    )

    for _ in range(iterations):
        monitor.available -= request_to_test
        monitor.allocation[process_id_to_test] += request_to_test
        monitor.need[process_id_to_test] -= request_to_test

        start_time = time.perf_counter()
        monitor._is_safe_state()
        end_time = time.perf_counter()
        total_time += end_time - start_time

        monitor.available += request_to_test
        monitor.allocation[process_id_to_test] -= request_to_test
        monitor.need[process_id_to_test] += request_to_test

    return total_time / iterations


# ==============================================================================
# 3. МАКРО-БЕНЧМАРК: ИЗМЕРЕНИЕ ПРОПУСКНОЙ СПОСОБНОСТИ СИСТЕМЫ
# ==============================================================================


class BenchmarkWorkerThread(threading.Thread):
    """Специальный воркер для бенчмарка: без sleep, без random."""

    def __init__(self, process_id, monitor, stop_event, results_list):
        super().__init__()
        self.process_id = process_id
        self.monitor = monitor
        self.stop_event = stop_event
        self.results_list = results_list
        self.successful_requests = 0

    def run(self):
        # Заявляем о максимальной потребности (например, половина всех ресурсов)
        max_claim = np.floor_divide(self.monitor.available, self.monitor.num_processes * 2)
        self.monitor.set_max_claim(self.process_id, max_claim)

        # Простой, детерминированный запрос
        request = np.floor_divide(max_claim, 2)
        if np.all(request == 0):
            request[0] = 1  # хотя бы 1 ресурс

        # Цикл "запрос-освобождение" на максимальной скорости
        while not self.stop_event.is_set():
            if self.monitor.request_resources(self.process_id, request):
                self.successful_requests += 1
                self.monitor.release_resources(self.process_id, request)

        # Сохраняем результат
        self.results_list.append(self.successful_requests)


def benchmark_throughput(num_processes, num_resources, duration=3):
    """Запускает полную симуляцию и измеряет кол-во операций в секунду."""
    total_resources = [100] * num_resources
    monitor = DeadlockPreventerMonitor(total_resources, num_processes, matrix_logger=DummyLogger())
    stop_event = threading.Event()
    results = []
    threads = []

    # Запускаем воркеры
    for i in range(num_processes):
        thread = BenchmarkWorkerThread(i, monitor, stop_event, results)
        threads.append(thread)
        thread.start()

    # Ждем указанное время
    time.sleep(duration)

    # Останавливаем все потоки
    stop_event.set()
    for thread in threads:
        thread.join()

    # Считаем и возвращаем пропускную способность
    total_operations = sum(results)
    return total_operations / duration


# ==============================================================================
# 4. ФУНКЦИИ ДЛЯ ЗАПУСКА ТЕСТОВ И ПОСТРОЕНИЯ ГРАФИКОВ
# ==============================================================================


def plot_results(data, title, xlabel, ylabel, filename):
    """Строит и сохраняет график."""
    x_vals = [item[0] for item in data]
    y_vals = [item[1] for item in data]

    plt.figure(figsize=(10, 6))
    plt.plot(x_vals, y_vals, marker="o", linestyle="-")
    plt.title(title, fontsize=16)
    plt.xlabel(xlabel, fontsize=12)
    plt.ylabel(ylabel, fontsize=12)
    plt.grid(True)
    plt.xticks(x_vals)
    plt.savefig(filename)
    print(f"График сохранен в файл: {filename}")
    plt.show()


def run_all_benchmarks():
    """Главная функция для запуска всех бенчмарков."""

    # --- Микро-бенчмарк: Зависимость от N и M ---
    print("--- 1. Запуск микро-бенчмарка (накладные расходы) ---")

    processes_to_test = [5, 10, 20, 50, 100, 150]
    times_vs_processes = []
    for n in processes_to_test:
        print(f"  Тестирование overhead с {n} процессами...")
        m = generate_random_state(n, [100] * 5)
        avg_time = benchmark_overhead(m) * 1e6  # в микросекундах
        times_vs_processes.append((n, avg_time))
    plot_results(
        times_vs_processes,
        "Зависимость времени проверки от числа процессов (N)",
        "Количество процессов",
        "Среднее время, мкс",
        "overhead_vs_processes.png",
    )

    # --- Макро-бенчмарк: Пропускная способность ---
    print("\n--- 2. Запуск макро-бенчмарка (пропускная способность) ---")

    processes_to_test_throughput = [1, 2, 4, 8, 12, 16, 24, 32]
    throughput_results = []
    for n in processes_to_test_throughput:
        print(f"  Тестирование throughput с {n} потоками...")
        ops_per_sec = benchmark_throughput(num_processes=n, num_resources=5)
        throughput_results.append((n, ops_per_sec))

    plot_results(
        throughput_results,
        "Пропускная способность системы",
        "Количество потоков-воркеров",
        "Операций (запрос+освобождение)/сек",
        "throughput_vs_threads.png",
    )


if __name__ == "__main__":
    run_all_benchmarks()
