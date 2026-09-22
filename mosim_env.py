import math
import time
import numpy as np
import gymnasium as gym
from gymnasium import spaces
import vgamepad as vg
from telemetry_receiver import MoSimTelemetryReceiver

class MoSimHuntEnv(gym.Env):
    metadata = {"render_modes": ["human"]}

    def __init__(self):
        super().__init__()
        self.telemetry = MoSimTelemetryReceiver(ip="127.0.0.1", port=9999)
        self.telemetry.start()
        self.gamepad = vg.VX360Gamepad()
        time.sleep(1.0)

        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(3,), dtype=np.float32)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(11,), dtype=np.float32)

        self.prev_pose = None
        self.prev_dist = 999.0
        self.step_count = 0
        self.max_steps = 3000  # Aumentado a ~60 segundos por intento

    def _get_obs(self, pose):
        closest_coral = self.telemetry.get_closest_piece(piece_type="CORAL")
        if closest_coral:
            tx, _, tz = closest_coral
        else:
            tx, tz = pose.x, pose.z

        dx = tx - pose.x
        dz = tz - pose.z
        dist = math.hypot(dx, dz)

        yaw_rad = math.radians(pose.yaw)
        target_yaw_rad = math.atan2(dx, dz)
        err_yaw = (target_yaw_rad - yaw_rad + math.pi) % (2 * math.pi) - math.pi

        vx = (pose.x - self.prev_pose.x) / 0.02 if self.prev_pose else 0.0
        vz = (pose.z - self.prev_pose.z) / 0.02 if self.prev_pose else 0.0
        omega = (pose.yaw - self.prev_pose.yaw) / 0.02 if self.prev_pose else 0.0

        is_coral = 1.0 if pose.piece_type == 1 else 0.0
        is_indexed = 1.0 if pose.is_indexed == 1 else 0.0

        obs = np.array([dx, dz, dist, math.sin(yaw_rad), math.cos(yaw_rad), err_yaw, 
                        vx, vz, omega, is_coral, is_indexed], dtype=np.float32)
        return obs, dist, err_yaw

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.step_count = 0
        
        # 1. Neutralizar mandos inmediatamente
        self.gamepad.left_joystick_float(0.0, 0.0)
        self.gamepad.right_joystick_float(0.0, 0.0)
        self.gamepad.left_trigger_float(0.0)
        self.gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN)
        self.gamepad.update()
        
        # 2. ESPERA INFINITA HASTA EL REINICIO MANUAL
        print("\n[ESPERANDO] Episodio terminado. Presiona 'R' en MoSimulator cuando estés listo...")
        
        last_pose = self.telemetry.get_pose()
        while True:
            current_pose = self.telemetry.get_pose()
            jump = math.hypot(current_pose.x - last_pose.x, current_pose.z - last_pose.z)
            
            if jump > 1.5:
                break
                
            last_pose = current_pose
            time.sleep(0.1)
            
        # 3. EL TIEMPO FUERA (20 segundos)
        print("\n[REINICIO DETECTADO] Tienes 20 seg. Si sale el brazo de algas, presiona la cruceta ARRIBA (RobotModeToggle) para regresar a Modo Coral.")
        time.sleep(20.0)
        print("[¡ACCIÓN!] Teleop iniciado. La IA retoma el control.")

        # 4. Preparar robot: Forzamos estado STOW con D-Pad Abajo
        self.gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN)
        self.gamepad.update()
        time.sleep(0.5)
        self.gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN)
        
        self.gamepad.left_trigger_float(1.0)
        self.gamepad.update()

        pose = self.telemetry.get_pose()
        self.prev_pose = pose
        obs, dist, _ = self._get_obs(pose)
        self.prev_dist = dist

        return obs, {}
    
    def step(self, action):
        self.step_count += 1
        strafe, forward, turn = float(action[0]), float(action[1]), float(action[2])

        self.gamepad.left_joystick_float(x_value_float=strafe, y_value_float=forward)
        self.gamepad.right_joystick_float(x_value_float=turn, y_value_float=0.0)
        
        pose = self.telemetry.get_pose()
        
        # --- LÓGICA DE ACTUADORES CORREGIDA (LT y D-Pad Abajo) ---
        if pose.piece_type == 1 and pose.is_indexed == 0:
            # Apagamos Intake (LT)
            self.gamepad.left_trigger_float(0.0) 
            # Mandamos la señal de Stow (D-Pad Abajo)
            self.gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN)
        else:
            if pose.piece_type == 0:
                self.gamepad.left_trigger_float(1.0)
            # Soltamos Stow
            self.gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN)
            
        self.gamepad.update()
        time.sleep(0.02)

        pose = self.telemetry.get_pose()
        obs, dist, err_yaw = self._get_obs(pose)

        reward = 0.0
        terminated = False
        truncated = self.step_count >= self.max_steps

        if math.hypot(pose.x - self.prev_pose.x, pose.z - self.prev_pose.z) > 1.5:
            print("\n[Manual] Teletransporte detectado. Forzando reinicio de episodio.")
            truncated = True

        reward += (self.prev_dist - dist) * 20.0
        reward -= 0.05

        if pose.piece_type == 2:
            reward -= 50.0
            terminated = True
            print("\n[Error] El robot engulló un Alga. Episodio abortado.")

        if pose.piece_type == 1 and pose.is_indexed == 0 and self.prev_pose.piece_type == 0:
            reward += 50.0
            print("\n[Progreso] ¡Coral capturado en el intake! Subiendo a STOW...")

        # Éxito maestro
        if pose.piece_type == 1 and pose.is_indexed == 1:
            reward += 200.0
            terminated = True
            print(f"\n[Exito] ¡Coral indexado en STOW en {self.step_count} pasos!")

        self.prev_dist = dist
        self.prev_pose = pose

        return obs, reward, terminated, truncated, {}
    
    def close(self):
        self.gamepad.left_joystick_float(0.0, 0.0)
        self.gamepad.right_joystick_float(0.0, 0.0)
        self.gamepad.left_trigger_float(0.0)
        self.gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN)
        self.gamepad.update()
        self.telemetry.stop()