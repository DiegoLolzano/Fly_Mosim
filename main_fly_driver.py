# main_fly_driver.py
import mss
import cv2
import numpy as np
import vgamepad as vg
import time
from perception import GamePerception
from fly_brain import SpikingFlyBrain

CAPTURE_REGION = {'top': 40, 'left': 10, 'width': 640, 'height': 480}

gamepad = vg.VX360Gamepad()
sct = mss.MSS()
detector = GamePerception(width=640, height=480)
brain = SpikingFlyBrain(n_sensory=5, n_neurons=128)

estado = "BUSCAR_CORAL"
has_piece = False
timer_fase = time.time()

print("Controlador calibrado para contacto y secuencia de score...")

try:
    while True:
        loop_start = time.time()
        scr_img = np.array(sct.grab(CAPTURE_REGION))
        frame = cv2.cvtColor(scr_img, cv2.COLOR_BGRA2BGR)

        features, clean_view = detector.extract_features(frame)
        robot = features["robot"]
        coral = features["coral"]
        reef = features["reef"]
        reef_area = features["reef_area"]

        gamepad.reset()
        move_x = 0.0
        move_y = 0.0
        turn_val = 0.0

        obs_stimulus = np.zeros(5, dtype=np.float32)

        if robot is not None:
            rx, ry = robot

            # 1. Buscar y capturar Coral
            if estado == "BUSCAR_CORAL":
                if coral is not None:
                    cx, cy = coral
                    dx = (cx - rx) / 120.0
                    dy = (cy - ry) / 120.0

                    move_x = float(np.clip(dx, -0.85, 0.85))
                    move_y = float(np.clip(-dy, -0.85, 0.85))
                    gamepad.left_trigger_float(value_float=1.0)  # Intake encendido

                    dist_px = np.hypot(cx - rx, cy - ry)
                    obs_stimulus[1] = 1.0 - np.clip(dist_px / 250.0, 0.0, 1.0)

                    if dist_px < 65 and (time.time() - timer_fase > 1.2):
                        has_piece = True
                        estado = "IR_A_REEF"
                        timer_fase = time.time()
                        print("Coral capturado -> Navegando hacia el Arrecife...")
                else:
                    # Búsqueda suave
                    turn_val = 0.60
                    move_y = -0.15

            # 2. Navegar al Arrecife
            elif estado == "IR_A_REEF":
                if reef is not None:
                    tx, ty = reef
                    dx = (tx - rx) / 140.0
                    dy = (ty - ry) / 140.0

                    move_x = float(np.clip(dx, -0.85, 0.85))
                    move_y = float(np.clip(-dy, -0.85, 0.85))

                    dist_px = np.hypot(tx - rx, ty - ry)
                    obs_stimulus[3] = 1.0 - np.clip(dist_px / 250.0, 0.0, 1.0)

                    # CRITERIO DE LLEGADA REAL:
                    # O bien la distancia en pantalla es menor a 210px (base del reef),
                    # o el área morada del Reef creció a más de 1200 px (está encima)
                    if dist_px < 210 or reef_area > 1200:
                        estado = "AUTOALINEAR_Y_SUBIR"
                        timer_fase = time.time()
                        print("¡Contacto con el Reef! Activando AutoAlign (LB) y Brazo L2 (B)...")
                else:
                    move_y = -0.35
                    turn_val = 0.40

            # 3. Autoalinear y elevar brazo
            elif estado == "AUTOALINEAR_Y_SUBIR":
                gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER) # Autoalign
                gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_B) # Nivel L2
                move_y = -0.15 # Empujar contra el AprilTag

                # 1 segundo completo para que el mástil termine de subir
                if time.time() - timer_fase > 1.0:
                    estado = "SOLTAR_CORAL"
                    timer_fase = time.time()
                    print("Mástil arriba -> Disparando Place (RT)...")

            # 4. Soltar pieza
            elif estado == "SOLTAR_CORAL":
                gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_B)
                gamepad.right_trigger_float(value_float=1.0)
                move_y = -0.05

                if time.time() - timer_fase > 1.1:
                    has_piece = False
                    estado = "DESPEGAR"
                    timer_fase = time.time()
                    print("Anotación completada -> Despegando del Reef...")

            # 5. Marcha atrás para librar el arrecife
            # 5. Marcha atrás real para regresar a la alianza propia
            elif estado == "DESPEGAR":
                move_y = -0.70  # <-- Valor NEGATIVO para retroceder hacia tu alianza (abajo en pantalla)
                move_x = 0.0
                gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_A)  # Bajar mástil (Stow)
                if time.time() - timer_fase > 1.2:
                    estado = "BUSCAR_CORAL"
                    timer_fase = time.time()
                    print("Regresando a zona de alianza -> Buscando siguiente coral.")

        # Inferencia neuronal
        _, spikes = brain.forward(obs_stimulus)
        total_spikes = int(np.sum(spikes))

        # Enviar comandos
        gamepad.left_joystick_float(x_value_float=move_x, y_value_float=move_y)
        gamepad.right_joystick_float(x_value_float=turn_val, y_value_float=0.0)
        gamepad.update()

        # Telemetría
        cv2.putText(clean_view, f"Estado: {estado}", (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)
        cv2.putText(clean_view, f"Area Reef: {int(reef_area)}", (15, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 0, 255), 2)
        cv2.putText(clean_view, f"Spikes: {total_spikes}/128", (15, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
        cv2.imshow("Driver Neuronal MoSim", clean_view)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        dt = time.time() - loop_start
        if dt < (1/60):
            time.sleep((1/60) - dt)

finally:
    cv2.destroyAllWindows()