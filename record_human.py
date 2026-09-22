# record_human.py
import mss
import cv2
import numpy as np
import pygame
import time
from perception import GamePerception

CAPTURE_REGION = {'top': 40, 'left': 10, 'width': 640, 'height': 480}

# Inicializar pygame solo para leer tu joystick real físico
pygame.init()
pygame.joystick.init()

if pygame.joystick.get_count() == 0:
    print("Conecta tu control real para grabar las partidas.")
    exit()

joystick = pygame.joystick.Joystick(0)
joystick.init()
print(f"Grabando desde: {joystick.get_name()}")

sct = mss.MSS()
detector = GamePerception(width=640, height=480)

obs_data = []
action_data = []

print("Maneja y anota en MoSim. Presiona Ctrl+C en la terminal para guardar y salir.")

try:
    while True:
        loop_start = time.time()
        pygame.event.pump()

        # 1. Leer mando físico
        # Ajusta los índices de ejes según tu control (común en Xbox: 1=Y izq, 4=X der)
        forward = -joystick.get_axis(1)  # Stick izq Y (invertido)
        turn = joystick.get_axis(4) if joystick.get_numaxes() > 4 else joystick.get_axis(2) # Stick der X
        intake = 1.0 if (joystick.get_button(4) or joystick.get_axis(2) > 0.5) else 0.0     # LB o LT
        place = 1.0 if (joystick.get_button(5) or joystick.get_axis(5) > 0.5) else 0.0      # RB o RT
        align = 1.0 if joystick.get_button(0) else 0.0                                       # Botón A

        # 2. Captura y percepción
        scr_img = np.array(sct.grab(CAPTURE_REGION))
        frame = cv2.cvtColor(scr_img, cv2.COLOR_BGRA2BGR)
        obs, _ = detector.extract_features(frame)

        obs_data.append(obs)
        action_data.append([forward, turn, intake, place, align])

        time.sleep(max(0, (1/30) - (time.time() - loop_start)))

except KeyboardInterrupt:
    print(f"\nGrabación terminada. Guardando {len(obs_data)} muestras...")
    np.savez("expert_demonstrations.npz", 
             obs=np.array(obs_data, dtype=np.float32), 
             actions=np.array(action_data, dtype=np.float32))
    print("Guardado en 'expert_demonstrations.npz'.")