import os
import threading
import time

import numpy as np


class ConsoleLogger:
    def __init__(self):
        self.log_lock = threading.Lock()

    def log(self, message, process_id=None):
        """Основной метод логирования с префиксом."""
        with self.log_lock:
            timestamp = f"{time.strftime('%H:%M:%S', time.localtime())}"
            if process_id is not None:
                prefix = f"{timestamp} [P{process_id}]"
                print(f"{prefix} {message}")
            else:
                prefix = f"{timestamp} [Monitor]"
                print(f"{prefix} {message}")

    def system(self, message):
        self.log(f"{message}")

    def request(self, pid, request_vec):
        self.log(f">> Запрашивает:  {request_vec}", process_id=pid)

    def success(self, pid, request_vec, available_vec):
        msg = f"++ УДОВЛЕТВОРЕН запрос {request_vec}. Доступно: {available_vec}"
        self.log(msg, process_id=pid)

    def release(self, pid, release_vec, available_vec):
        msg = f"<< Освободил ресурсы: {release_vec}. Доступно: {available_vec}"
        self.log(msg, process_id=pid)

    def wait(self, pid, request_vec, available_vec):
        msg = f"-- ЖДЕТ. Запрос {request_vec} > Доступно {available_vec}"
        self.log(msg, process_id=pid)

    def deferred(self, pid, request_vec):
        msg = f"-- ОТЛОЖЕНО! Запрос {request_vec} ведет к небезопасной ситуации. Откат."
        self.log(msg, process_id=pid)

    def error(self, pid, message):
        self.log(f"!! ОШИБКА: {message}", process_id=pid)

    def info(self, pid, message):
        self.log(f"{message}", process_id=pid)


class MatrixFileLogger:
    def __init__(self, filename="deadlock_log.txt", num_processes=0, resource_names=None):
        if os.path.exists(filename):
            os.remove(filename)
        self.file_handle = open(filename, "w", encoding="utf-8")
        self.lock = threading.Lock()
        self.num_processes = num_processes
        self.resource_names = resource_names or [f"R{i}" for i in range(10)]

    def log_state(self, event_description, monitor_state):
        with self.lock:
            np_format = {"suppress_small": True, "precision": 0}
            self.file_handle.write(f"\n{'='*80}\n")
            self.file_handle.write(f"СОБЫТИЕ: {event_description}\n")
            self.file_handle.write(f"Время:   {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n")
            self.file_handle.write(f"{'-'*80}\n")

            available_str = np.array2string(monitor_state.available, **np_format)
            self.file_handle.write(f"Доступно (Available): {available_str}\n\n")

            header = "         " + "  ".join(
                [f"{name:<4}" for name in self.resource_names[: monitor_state.num_resources]]
            )

            self.file_handle.write("Матрица выделено (Allocation):\n")
            self.file_handle.write(header + "\n")
            for i in range(self.num_processes):
                row = (
                    np.array2string(monitor_state.allocation[i], **np_format).replace("[", "").replace("]", "").strip()
                )
                self.file_handle.write(f"Процесс P{i}: {row}\n")

            self.file_handle.write("\nМатрица потребностей (Need):\n")
            self.file_handle.write(header + "\n")
            for i in range(self.num_processes):
                row = np.array2string(monitor_state.need[i], **np_format).replace("[", "").replace("]", "").strip()
                self.file_handle.write(f"Процесс P{i}: {row}\n")

            self.file_handle.write(f"{'='*80}\n")
            self.file_handle.flush()

    def close(self):
        with self.lock:
            self.file_handle.close()


logger = ConsoleLogger()
