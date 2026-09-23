import math
import keyboard
import pickle
import random
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
        
        self.max_steps = 1000  # Agrega esta línea (ajusta el número si usabas otro)
        
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(3,), dtype=np.float32)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(11,), dtype=np.float32)
        # ... el resto de tu código ...

        # --- TU CÓDIGO ORIGINAL (Gamepad, Telemetría, etc) ---
        self.gamepad = vg.VX360Gamepad()
        self.telemetry = MoSimTelemetryReceiver()
        # ... 

        # --- CARGAR MACROS PROCEDURALES ---
        print("[Info] Cargando rutinas de inicialización procedural...")
        # Asegúrate de que todas digan 'macros/' y no 'marcos/'
        try:
            with open('macros/ruta_roja_constante.pkl', 'rb') as f:
                self.macro_roja = pickle.load(f)
            
            with open('macros/ruta_azul_1.pkl', 'rb') as f:
                self.macro_azul_1 = pickle.load(f)
            
            with open('macros/ruta_azul_2.pkl', 'rb') as f:
                self.macro_azul_2 = pickle.load(f)
                
            with open('macros/ruta_verde_1.pkl', 'rb') as f:
                self.macro_verde_1 = pickle.load(f)
            # Si grabaste más, agrégalas aquí siguiendo el mismo formato
            print("[Info] ¡Macros cargadas con éxito!")
        except FileNotFoundError as e:
            print(f"[Advertencia] No se encontró el archivo de macro: {e}")

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
        target_yaw_rad = math.atan2(-dx, -dz)
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
        
        # 1. Asegurar que el control de Xbox virtual esté neutralizado
        self.gamepad.left_joystick_float(0.0, 0.0)
        self.gamepad.right_joystick_float(0.0, 0.0)
        self.gamepad.left_trigger_float(0.0)
        self.gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN)
        self.gamepad.update()
        
        print(f"\n[Episodio] Iniciando auto-reset. Aplicando Domain Randomization...")
        
        # 2. Reiniciar el simulador (Tecla R nativa)
        keyboard.send('r')
        time.sleep(1.0) # Tiempo para que respawnee el robot y las piezas
        
        # 3. EJECUTAR EL CAOS PROCEDURAL
        # Ruta Constante (Salir y escupir)
        keyboard.play(self.macro_roja)
        
        # Ruta Azul (Dispersión de piezas) - Elige al azar
        caos_azul = random.choice([self.macro_azul_1, self.macro_azul_2])
        keyboard.play(caos_azul)
        
        # Ruta Verde (Posicionamiento final de la IA) - Si tienes más de 1, ponlas en la lista
        caos_verde = random.choice([self.macro_verde_1]) 
        keyboard.play(caos_verde)
        
        # 4. QUEMAR EL TIEMPO RESTANTE DE GRACIA
        # keyboard.play ejecuta las acciones en tiempo real. 
        # Pon aquí un time.sleep() aproximado de lo que falte para llegar a los 20 segundos.
        # Por ejemplo, si tus macros duran unos 12 segundos, pon 8.0 aquí.
        time.sleep(8.0) 
        
        # 5. ENTREGAR EL CONTROL AL AGENTE PPO
        # Forzar estado Stow y prender el intake
        keyboard.send('z')
        time.sleep(0.5)
        self.gamepad.left_trigger_float(1.0)
        self.gamepad.update()

        # Tomar la primera observación oficial
        pose = self.telemetry.get_pose()
        self.prev_pose = pose
        obs, dist, _ = self._get_obs(pose)
        self.prev_dist = dist

        print("[¡ACCIÓN!] Modo Teleop habilitado. La Mosca entra en cacería.")
        return obs, {}
    
    def step(self, action):
        self.step_count += 1
        strafe, forward, turn = float(action[0]), float(action[1]), float(action[2])

        # Traslación Field-Centric (directo a los joysticks)
        self.gamepad.left_joystick_float(x_value_float=strafe, y_value_float=forward)
        self.gamepad.right_joystick_float(x_value_float=turn, y_value_float=0.0)
        
        pose = self.telemetry.get_pose()
        
        macro_success = False  
        
        # --- MACRO DE STOW (VICTORIA INCONDICIONAL) ---
        if pose.piece_type == 1 and pose.is_indexed == 0:
            print("\n[Progreso] ¡Coral detectado! Ejecutando Macro de STOW ciega...")
            
            # Frenamos llantas
            self.gamepad.left_joystick_float(0.0, 0.0)
            self.gamepad.right_joystick_float(0.0, 0.0)
            
            # Apagamos rodillos 
            self.gamepad.left_trigger_float(0.0)
            self.gamepad.update()
            time.sleep(0.15) 
            
            # Mantenemos presionado Stow
            self.gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN)
            self.gamepad.update()
            
            # 2.5 segundos de pausa ABSOLUTA.
            time.sleep(2.5)
            
            # ¡Declaramos la victoria sin preguntarle a los sensores!
            macro_success = True
                    
            # Soltamos Stow 
            self.gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN)
            self.gamepad.update()
            time.sleep(0.1) 
            
            pose = self.telemetry.get_pose()

        # Comportamiento normal si no está stoweando
        else:
            if pose.piece_type == 0:
                self.gamepad.left_trigger_float(1.0) 
            else:
                self.gamepad.left_trigger_float(0.0) 
            self.gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN)
            self.gamepad.update()
            time.sleep(0.02)

        pose = self.telemetry.get_pose()
        obs, dist, err_yaw = self._get_obs(pose)

        reward = 0.0
        terminated = False
        truncated = self.step_count >= self.max_steps

        if math.hypot(pose.x - self.prev_pose.x, pose.z - self.prev_pose.z) > 4.0:
            print("\n[Manual] Teletransporte detectado. Forzando reinicio.")
            truncated = True

        # --- CASTIGO POR CHOQUE / ATASCO ---
        # Sumamos la fuerza que la IA está intentando mandar a las llantas
        esfuerzo_motores = abs(forward) + abs(strafe)
        # Calculamos cuánto se movió realmente en este instante
        velocidad_real = math.hypot(pose.x - self.prev_pose.x, pose.z - self.prev_pose.z)
        
        # Si la IA acelera a fondo pero el chasis casi no se mueve...
        if esfuerzo_motores > 0.5 and velocidad_real < 0.02:
            reward -= 2.0  # Penalización severa por quemar llanta contra obstáculos

        # Recompensa por acortar distancia
        reward += (self.prev_dist - dist) * 20.0
        
        # Castigo por desalineación angular
        reward -= abs(err_yaw) * 0.5 
        
        # Penalización por tiempo
        reward -= 0.05

        if pose.piece_type == 2:
            reward -= 50.0
            terminated = True
            print("\n[Error] El robot engulló un Alga. Episodio abortado.")

        if pose.piece_type == 1 and self.prev_pose.piece_type == 0:
            reward += 50.0

        # ÉXITO MAESTRO: Validado incondicionalmente por la macro
        if macro_success or pose.is_indexed == 1:
            reward += 200.0
            terminated = True
            print(f"\n[Exito] ¡Coral asegurado en el End Effector en {self.step_count} pasos!")

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