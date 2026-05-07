class Logger:
    def log_step(self, agent, obs, action, reward):
        pass

    def log_episode_end(self):
        pass


class PrintLogger(Logger):
    def log_step(self, agent, obs, action, reward):
        print(f"{agent} | action={action} | reward={reward}")

    def log_episode_end(self):
        print("Episode finished\n")


class CsvLogger(Logger):
    """
    CSV logger that writes one row per step with columns:
    timestamp, episode, step, agent, action, reward, obs (repr)
    Usage:
      logger = CsvLogger("run_logs.csv")                 # single file, append
      logger = CsvLogger("logs", per_episode=True)       # creates logs/YYYYMMDD_HHMMSS_episode_<n>.csv
    """

    fieldnames = ["timestamp", "episode", "step", "agent", "action", "reward", "obs"]

    def __init__(self, path, per_episode=False, newline="", flush=True):
        """
        path: filename or directory (if per_episode=True)
        per_episode: if True, create a new file for each episode inside `path` dir
        newline: passed to open() to control newlines; default "" works cross-platform
        flush: flush after each write (useful to inspect file while running)
        """
        self.per_episode = per_episode
        self.flush = flush
        self.episode = 0
        self.step = 0

        if self.per_episode:
            os.makedirs(path, exist_ok=True)
            self.dir = path
            self._open_new_episode_file()
        else:
            # single file mode: path is a filename
            self.filepath = path
            new_file = not os.path.exists(self.filepath)
            self._open_file(self.filepath, newline)
            if new_file:
                self._writer.writeheader()

    def _open_file(self, filepath, newline=""):
        # Keep file and writer as attributes
        self._file = open(filepath, mode="a", newline=newline, encoding="utf-8")
        self._writer = csv.DictWriter(self._file, fieldnames=self.fieldnames)

    def _open_new_episode_file(self):
        self.episode += 1
        self.step = 0
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_episode_{self.episode}.csv"
        self.filepath = os.path.join(self.dir, filename)
        self._open_file(self.filepath)
        self._writer.writeheader()

    def log_step(self, agent, obs, action, reward):
        """
        Call this each environment step. 'obs' is stored as repr(obs) to keep CSV safe.
        """
        self.step += 1
        row = {
            "timestamp": datetime.utcnow().isoformat(),
            "episode": self.episode,
            "step": self.step,
            "agent": str(agent),
            "action": str(action),
            "reward": float(reward) if reward is not None else "",
            "obs": repr(obs),
        }
        self._writer.writerow(row)
        if self.flush:
            self._file.flush()
            os.fsync(self._file.fileno())

    def log_episode_end(self):
        """
        Ends current episode. In per_episode mode the file is closed and a new one opened.
        In single-file mode just updates episode counter and writes a blank separator row.
        """
        # write a separator row (empty values) to mark episode boundary in single-file mode
        if self.per_episode:
            try:
                self._file.close()
            except Exception:
                pass
            self._open_new_episode_file()
        else:
            # separator row with episode increment
            self.episode += 1
            self.step = 0
            separator = {
                "timestamp": datetime.utcnow().isoformat(),
                "episode": self.episode,
                "step": "",
                "agent": "",
                "action": "EPISODE_END",
                "reward": "",
                "obs": "",
            }
            self._writer.writerow(separator)
            if self.flush:
                self._file.flush()
                os.fsync(self._file.fileno())

    def close(self):
        try:
            self._file.close()
        except Exception:
            pass
