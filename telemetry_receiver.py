import socket
import threading
from dataclasses import dataclass
from typing import List, Tuple, Optional
import math

@dataclass
class RobotPose:
    name: str = ""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    yaw: float = 0.0
    piece_type: int = 0  # 0: Nada, 1: Coral, 2: Alga
    is_indexed: int = 0  # 0: Hopper (Abajo), 1: End-Effector (STOW)

@dataclass
class GamePiece:
    type: str  # "CORAL" o "ALGAE"
    x: float
    y: float
    z: float

class MoSimTelemetryReceiver:
    def __init__(self, ip="127.0.0.1", port=9999):
        self.ip = ip
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.ip, self.port))
        self.sock.settimeout(1.0)
        
        self.pose = RobotPose()
        self.corals: List[GamePiece] = []
        self.algae: List[GamePiece] = []
        
        self.running = False
        self.thread = None
        self.lock = threading.Lock()

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        self.sock.close()

    def _receive_loop(self):
        while self.running:
            try:
                data, _ = self.sock.recvfrom(8192) # Buffer ampliado para soportar más algas/corales
                msg = data.decode('utf-8')
                self._parse_message(msg)
            except socket.timeout:
                continue
            except Exception as e:
                pass # Ignorar errores de decodificación aislados

    def _parse_message(self, msg: str):
        parts = msg.split('|')
        if not parts:
            return
            
        rob_parts = parts[0].split(',')
        if len(rob_parts) >= 8 and rob_parts[0] == "ROBOT":
            with self.lock:
                self.pose.name = rob_parts[1]
                self.pose.x = float(rob_parts[2])
                self.pose.y = float(rob_parts[3])
                self.pose.z = float(rob_parts[4])
                self.pose.yaw = float(rob_parts[5])
                self.pose.piece_type = int(rob_parts[6])
                self.pose.is_indexed = int(rob_parts[7])
                
                self.corals.clear()
                self.algae.clear()
                
                for p in parts[1:]:
                    p_data = p.split(',')
                    if len(p_data) >= 4:
                        g_type = p_data[0]
                        x, y, z = float(p_data[1]), float(p_data[2]), float(p_data[3])
                        piece = GamePiece(g_type, x, y, z)
                        
                        if g_type == "CORAL":
                            self.corals.append(piece)
                        elif g_type == "ALGAE":
                            self.algae.append(piece)

    def get_pose(self) -> RobotPose:
        with self.lock:
            return RobotPose(
                self.pose.name, self.pose.x, self.pose.y, self.pose.z, self.pose.yaw,
                self.pose.piece_type, self.pose.is_indexed
            )

    def get_corals(self) -> List[GamePiece]:
        with self.lock:
            return list(self.corals)

    def get_algae(self) -> List[GamePiece]:
        with self.lock:
            return list(self.algae)
            
    def get_closest_piece(self, piece_type="CORAL", center_point=None, max_dist=999.0) -> Optional[Tuple[float, float, float]]:
        """Devuelve (x, y, z) de la pieza más cercana del tipo especificado."""
        with self.lock:
            ref_x = center_point[0] if center_point else self.pose.x
            ref_z = center_point[1] if center_point else self.pose.z
            
            pieces = self.corals if piece_type == "CORAL" else self.algae
            
            closest = None
            min_d = max_dist
            
            for p in pieces:
                d = math.hypot(p.x - ref_x, p.z - ref_z)
                if d < min_d:
                    min_d = d
                    closest = (p.x, p.y, p.z)
                    
            return closest