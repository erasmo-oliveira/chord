"""Canal de mensagens usado por chord.py.

A interface é a do pacote channel do livro: join, sendTo, recvFromAny e
recvFrom. A implementação daqui é local, em TCP, para o laboratório rodar
só com a biblioteca padrão. O processo que cria o canal com flush=True
sobe o corretor; os demais processos se conectam a ele.
"""

import pickle
import socket
import threading
import time

HOST = "127.0.0.1"
BASE_PORT = 17640


def _send(sock, obj):
    data = pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)
    sock.sendall(len(data).to_bytes(4, "big") + data)


def _recv(sock):
    header = _recvn(sock, 4)
    size = int.from_bytes(header, "big")
    return pickle.loads(_recvn(sock, size))


def _recvn(sock, size):
    chunks = []
    remaining = size
    while remaining:
        chunk = sock.recv(remaining)
        if not chunk:
            raise ConnectionError("conexão do canal fechada")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


class _Broker(threading.Thread):
    def __init__(self, port):
        super().__init__(daemon=True)
        self.port = port
        self._stop = threading.Event()
        self._cond = threading.Condition()
        self.members = set()
        self.inbox = {}
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server.bind((HOST, port))
        except OSError as exc:
            raise RuntimeError(
                "porta %s ocupada; encerre a execução anterior do laboratório" % port
            ) from exc
        server.listen()
        server.settimeout(0.2)
        self._server = server

    def run(self):
        server = self._server
        while not self._stop.is_set():
            try:
                conn, _addr = server.accept()
            except socket.timeout:
                continue
            threading.Thread(target=self._serve, args=(conn,), daemon=True).start()
        server.close()

    def stop(self):
        self._stop.set()
        with self._cond:
            self._cond.notify_all()

    def _serve(self, conn):
        try:
            while not self._stop.is_set():
                cmd = _recv(conn)
                reply = self._handle(cmd)
                _send(conn, reply)
        except (ConnectionError, EOFError, OSError):
            return
        finally:
            conn.close()

    def _handle(self, cmd):
        op = cmd[0]
        with self._cond:
            if op == "join":
                pid = int(cmd[1])
                if pid in self.members:
                    return ("err", "identificador %s já entrou no canal" % pid)
                self.members.add(pid)
                self.inbox.setdefault(pid, [])
                self._cond.notify_all()
                return ("ok",)
            if op == "members":
                return ("ok", sorted(self.members))
            if op == "send":
                sender = int(cmd[1])
                destinations = [int(dest) for dest in cmd[2]]
                missing = [dest for dest in destinations if dest not in self.members]
                if missing:
                    return (
                        "err",
                        "destino %s não entrou no canal; a busca precisa começar num nó do anel"
                        % missing[0],
                    )
                for dest in destinations:
                    self.inbox.setdefault(dest, []).append((sender, cmd[3]))
                self._cond.notify_all()
                return ("ok",)
            if op == "recv":
                pid = int(cmd[1])
                wanted = cmd[2]
                while not self._stop.is_set():
                    box = self.inbox.setdefault(pid, [])
                    for index, (sender, message) in enumerate(box):
                        if wanted is None or sender in wanted:
                            box.pop(index)
                            return ("msg", sender, message)
                    self._cond.wait()
                return ("err", "canal encerrado")
        return ("err", "comando desconhecido: %s" % op)


class Channel:
    def __init__(self, channelID, flush=False):
        self.channelID = int(channelID)
        self.port = BASE_PORT + self.channelID
        self.pid = None
        self._sock = None
        self._io = threading.Lock()
        self._broker = None
        if flush:
            self._broker = _Broker(self.port)
            self._broker.start()

    def _rpc(self, cmd):
        self._connect()
        with self._io:
            _send(self._sock, cmd)
            reply = _recv(self._sock)
        if reply[0] == "err":
            raise RuntimeError(reply[1])
        return reply

    def _connect(self):
        if self._sock is not None:
            return
        last = None
        for _attempt in range(50):
            try:
                sock = socket.create_connection((HOST, self.port), timeout=2)
            except OSError as exc:
                last = exc
                time.sleep(0.05)
                continue
            sock.settimeout(None)
            self._sock = sock
            return
        raise ConnectionError(
            "corretor do canal %s não está acessível em %s:%s (%s)"
            % (self.channelID, HOST, self.port, last)
        )

    def join(self, newpid):
        self.pid = int(newpid)
        self._rpc(("join", self.pid))

    def members(self):
        return self._rpc(("members",))[1]

    def wait_for_members(self, count, timeout=10):
        deadline = time.time() + timeout
        while time.time() < deadline:
            joined = self.members()
            if len(joined) >= count:
                return joined
            time.sleep(0.02)
        raise TimeoutError("só %s processos entraram no canal" % len(self.members()))

    def sendTo(self, destination, message):
        if isinstance(destination, int):
            destinations = [destination]
        else:
            destinations = [int(item) for item in destination]
        self._rpc(("send", self.pid, destinations, message))

    def recvFromAny(self, timeout=0):
        del timeout
        reply = self._rpc(("recv", self.pid, None))
        return (reply[1], reply[2])

    def recvFrom(self, senderSet, timeout=0):
        del timeout
        if isinstance(senderSet, int):
            wanted = {int(senderSet)}
        else:
            wanted = {int(item) for item in senderSet}
        reply = self._rpc(("recv", self.pid, wanted))
        return (reply[1], reply[2])
